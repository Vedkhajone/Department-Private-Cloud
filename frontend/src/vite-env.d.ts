/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Set in .env -- see components/Footer.tsx.
  readonly VITE_APP_VERSION: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
