declare module "*apps/web/node_modules/@playwright/test/index.mjs" {
  export const test: typeof import("<DIAGNOSIS_CACHE>/fixed-source-01/apps/web/node_modules/@playwright/test").test
  export const expect: typeof import("<DIAGNOSIS_CACHE>/fixed-source-01/apps/web/node_modules/@playwright/test").expect
  export type BrowserContext = import("<DIAGNOSIS_CACHE>/fixed-source-01/apps/web/node_modules/@playwright/test").BrowserContext
  export type BrowserType = import("<DIAGNOSIS_CACHE>/fixed-source-01/apps/web/node_modules/@playwright/test").BrowserType
  export type Page = import("<DIAGNOSIS_CACHE>/fixed-source-01/apps/web/node_modules/@playwright/test").Page
}
