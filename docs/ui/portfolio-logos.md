# Indian portfolio company logos

188 locally cached marks cover 188 unique holdings in the public India catalog captured on 3 October 2026. Source URLs and matching company names are recorded in src/data/indiaCompanyLogos.json. NSE symbol matching uses TradingView's India instrument metadata; BAJAJ-AUTO maps to BAJAJ_AUTO there. Brand marks may be shared within corporate groups.

VAML and KIRLPNU use PNG logos downloaded from their official company websites. Future holdings receive the same fallback. Images load lazily from this site's own assets; failed images also fall back to initials. No price, weight, tracking, or access-control rules changed.

Validation: production build passed; all downloaded files parse as SVG and contain no script, foreignObject, or event attributes. Browser visual verification was unavailable because the in-app browser connection was unavailable.

## Deployment correction and company identity audit

The public /company-logos URLs were returning SPA HTML even after the prior workflow completed. CompanyLogo now imports the images through Vite so they are emitted under the working /assets path (or embedded as image data). This removes the dependency on a separately served directory.

Replaced generic group mappings for TCS, Tata Consumer, Adani Enterprises, Adani Power and the Tata Motors entries. Tata Consumer, Adani Enterprises, Adani Power and Tata Motors use original files from their official sites. TCS's official download rejected direct access, so its company-specific Simple Icons mark is used, with the official branding reference retained in the manifest. Other holdings retain their NSE-matched market-data-provider marks. This is not a claim that every image was independently sourced from its company's website.
