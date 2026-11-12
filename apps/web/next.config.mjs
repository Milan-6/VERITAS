/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'https://veritas-backend-3cge.onrender.com/api/v1/:path*',
      },
    ];
  },
};

export default nextConfig;