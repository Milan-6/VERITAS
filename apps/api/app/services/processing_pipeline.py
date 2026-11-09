import logging
import traceback
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.document import (
    Document,
    DocumentMetadata,
    DocumentProcessingJob,
    ExtractedPage,
    ExtractedSection,
    ExtractedContent,
    DocumentStatus,
    JobStatus,
    ProcessingStage,
)
from app.models.chunk import SemanticChunk
from app.services.pdf_parser import pdf_parser_service
from app.services.chunker import semantic_chunker
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)


class DocumentProcessingPipeline:
    def process_document_job(self, job_id: str, db: Session | None = None) -> bool:
        """
        Executes the end-to-end PDF processing pipeline for a specific job:
        VALIDATION -> PARSING -> TEXT_EXTRACTION -> LAYOUT_ANALYSIS ->
        METADATA_EXTRACTION -> SECTION_RECOGNITION -> PAGE_MAPPING -> PERSISTENCE -> COMPLETED
        """
        own_session = False
        if db is None:
            db = SessionLocal()
            own_session = True

        try:
            job = db.query(DocumentProcessingJob).filter(DocumentProcessingJob.id == job_id).first()
            if not job:
                logger.error(f"Job {job_id} not found")
                return False

            doc = db.query(Document).filter(Document.id == job.document_id).first()
            if not doc:
                logger.error(f"Document {job.document_id} not found for job {job_id}")
                job.status = JobStatus.FAILED.value
                job.error_details = "Associated document not found"
                db.commit()
                return False

            # Prevent duplicate execution if already running
            if job.status == JobStatus.RUNNING.value:
                logger.warning(f"Job {job_id} is already running. Skipping duplicate run.")
                return False

            # Update state to RUNNING
            job.status = JobStatus.RUNNING.value
            job.attempts += 1
            job.started_at = datetime.utcnow()
            doc.status = DocumentStatus.PROCESSING.value
            doc.error_message = None

            # Stage 1: VALIDATION
            job.stage = ProcessingStage.VALIDATION.value
            job.progress_pct = 10.0
            db.commit()

            # Stage 2: PARSING & LAYOUT ANALYSIS
            job.stage = ProcessingStage.PARSING.value
            job.progress_pct = 25.0
            db.commit()

            # Execute extraction
            parsed = pdf_parser_service.parse_pdf(doc.storage_path, doc.id)

            # Stage 3: TEXT EXTRACTION & METADATA
            job.stage = ProcessingStage.METADATA_EXTRACTION.value
            job.progress_pct = 50.0
            db.commit()

            # Clean existing extractions and chunks if retrying
            db.query(SemanticChunk).filter(SemanticChunk.document_id == doc.id).delete()
            db.query(ExtractedContent).filter(ExtractedContent.document_id == doc.id).delete()
            db.query(ExtractedSection).filter(ExtractedSection.document_id == doc.id).delete()
            db.query(ExtractedPage).filter(ExtractedPage.document_id == doc.id).delete()
            db.query(DocumentMetadata).filter(DocumentMetadata.document_id == doc.id).delete()
            db.flush()

            # Clean any old vectors in Qdrant
            vector_store.delete_document_vectors(doc.id)

            # Persist Metadata
            meta_record = DocumentMetadata(
                document_id=doc.id,
                title=parsed.title,
                authors=parsed.authors,
                abstract=parsed.abstract,
                keywords=parsed.keywords,
                publication_date=parsed.publication_date,
                doi=parsed.doi,
                journal_or_conference=parsed.journal_or_conference,
                total_pages=parsed.total_pages,
                raw_metadata=parsed.raw_metadata,
            )
            db.add(meta_record)

            # Stage 4: SECTION RECOGNITION
            job.stage = ProcessingStage.SECTION_RECOGNITION.value
            job.progress_pct = 60.0
            db.commit()

            sec_id_map = {}
            for sec in parsed.sections:
                sec_rec = ExtractedSection(
                    document_id=doc.id,
                    section_title=sec.section_title,
                    section_level=sec.section_level,
                    start_page=sec.start_page,
                    end_page=sec.end_page,
                    order_index=sec.order_index,
                )
                db.add(sec_rec)
                db.flush()
                sec_id_map[sec.section_title.lower()] = sec_rec.id

            # Stage 5: PAGE MAPPING & PROVENANCE
            job.stage = ProcessingStage.PAGE_MAPPING.value
            job.progress_pct = 75.0
            db.commit()

            page_id_map = {}
            for p in parsed.pages:
                page_rec = ExtractedPage(
                    document_id=doc.id,
                    page_number=p.page_number,
                    width=p.width,
                    height=p.height,
                    text_length=p.text_length,
                    has_images=p.has_images,
                    has_tables=p.has_tables,
                )
                db.add(page_rec)
                db.flush()
                page_id_map[p.page_number] = page_rec.id

            # Stage 6: CONTENT PERSISTENCE
            job.stage = ProcessingStage.PERSISTENCE.value
            job.progress_pct = 85.0
            db.commit()

            for item in parsed.contents:
                content_rec = ExtractedContent(
                    document_id=doc.id,
                    page_id=page_id_map.get(item.page_number),
                    section_id=sec_id_map.get(item.section.lower()),
                    chunk_id=item.chunk_id,
                    content_type=item.content_type,
                    source_text=item.source_text,
                    page_number=item.page_number,
                    section=item.section,
                    subsection=item.subsection,
                    extraction_method=item.extraction_method,
                    bounding_box=item.bounding_box,
                    order_index=item.order_index,
                )
                db.add(content_rec)
            db.flush()

            # Stage 7: SEMANTIC CHUNKING (Milestone 2)
            job.stage = ProcessingStage.CHUNKING.value
            job.progress_pct = 90.0
            db.commit()

            chunk_data_list = semantic_chunker.chunk_extracted_nodes(
                document_id=doc.id,
                document_title=parsed.title,
                extracted_contents=parsed.contents,
            )

            tenant_id = doc.workspace_id or doc.user_id
            chunk_records: list[SemanticChunk] = []

            for c_data in chunk_data_list:
                s_chunk = SemanticChunk(
                    document_id=doc.id,
                    user_id=doc.user_id,
                    workspace_id=doc.workspace_id,
                    chunk_id=c_data.chunk_id,
                    page_number=c_data.page_number,
                    section_title=c_data.section_title,
                    subsection=c_data.subsection,
                    context_header=c_data.context_header,
                    content_text=c_data.content_text,
                    embedded_text=c_data.embedded_text,
                    token_count=c_data.token_count,
                    chunk_index=c_data.chunk_index,
                    is_indexed=False,
                )
                db.add(s_chunk)
                chunk_records.append(s_chunk)

            db.flush()

            # Stage 8: VECTOR INDEXING (Milestone 3 & 4)
            job.stage = ProcessingStage.VECTOR_INDEXING.value
            job.progress_pct = 95.0
            db.commit()

            if chunk_records:
                point_ids = vector_store.index_chunks(
                    tenant_id=tenant_id,
                    document_id=doc.id,
                    document_title=parsed.title,
                    chunks=chunk_records,
                )
                for s_chunk, pid in zip(chunk_records, point_ids):
                    s_chunk.qdrant_point_id = pid
                    s_chunk.is_indexed = True

            # Mark Completed
            job.status = JobStatus.COMPLETED.value
            job.stage = ProcessingStage.COMPLETED.value
            job.progress_pct = 100.0
            job.completed_at = datetime.utcnow()
            doc.status = DocumentStatus.COMPLETED.value
            doc.error_message = None
            db.commit()
            return True

        except Exception as e:
            db.rollback()
            err_msg = str(e)
            tb = traceback.format_exc()
            logger.error(f"Processing error for job {job_id}: {err_msg}\n{tb}")

            # Re-fetch records in fresh state to update failure
            try:
                job = db.query(DocumentProcessingJob).filter(DocumentProcessingJob.id == job_id).first()
                if job:
                    job.status = JobStatus.FAILED.value
                    job.error_details = f"{err_msg}\n{tb[:500]}"
                    job.completed_at = datetime.utcnow()
                doc = db.query(Document).filter(Document.id == job.document_id).first() if job else None
                if doc:
                    doc.status = DocumentStatus.FAILED.value
                    doc.error_message = err_msg
                db.commit()
            except Exception as inner_e:
                logger.error(f"Failed to record failure status: {inner_e}")

            return False

        finally:
            if own_session:
                db.close()


processing_pipeline = DocumentProcessingPipeline()
