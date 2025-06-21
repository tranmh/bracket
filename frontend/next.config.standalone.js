/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export configuration
  output: 'export',
  trailingSlash: true,
  skipTrailingSlashRedirect: true,
  
  // Output to standalone directory
  distDir: '../standalone/dist/frontend',
  
  // Standalone environment configuration
  env: {
    NEXT_PUBLIC_API_BASE_URL: 'http://localhost:8400',
    NEXT_PUBLIC_MODE: 'standalone'
  },
  
  // Image optimization must be disabled for static export
  images: {
    unoptimized: true
  },
  
  // Preserve existing configuration
  reactStrictMode: true,
  swcMinify: true,
  
  // Handle routing for static files
  assetPrefix: process.env.NODE_ENV === 'production' ? '.' : '',
}

module.exports = nextConfig