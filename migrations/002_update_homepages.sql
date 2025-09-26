-- Update venue.homepage based on venue name patterns (idempotent)
-- Only fill when homepage is NULL or empty

-- IEEE
UPDATE scholar.venue
SET homepage = 'https://ieeexplore.ieee.org'
WHERE (homepage IS NULL OR trim(homepage) = '') AND name ILIKE '%IEEE%';

-- ACM
UPDATE scholar.venue
SET homepage = 'https://dl.acm.org'
WHERE (homepage IS NULL OR trim(homepage) = '') AND name ILIKE '%ACM%';

-- Elsevier / ScienceDirect
UPDATE scholar.venue
SET homepage = 'https://www.sciencedirect.com'
WHERE (homepage IS NULL OR trim(homepage) = '') AND (name ILIKE '%Elsevier%' OR name ILIKE '%ScienceDirect%');

-- Springer
UPDATE scholar.venue
SET homepage = 'https://link.springer.com'
WHERE (homepage IS NULL OR trim(homepage) = '') AND name ILIKE '%Springer%';

-- Nature / NPG
UPDATE scholar.venue
SET homepage = 'https://www.nature.com'
WHERE (homepage IS NULL OR trim(homepage) = '') AND (name ILIKE '%Nature%' OR name ILIKE '%NPG%');

-- Wiley
UPDATE scholar.venue
SET homepage = 'https://onlinelibrary.wiley.com'
WHERE (homepage IS NULL OR trim(homepage) = '') AND name ILIKE '%Wiley%';

-- PLOS
UPDATE scholar.venue
SET homepage = 'https://plos.org'
WHERE (homepage IS NULL OR trim(homepage) = '') AND (name ILIKE '%PLOS%' OR name ILIKE '%Public Library of Science%');

-- Frontiers
UPDATE scholar.venue
SET homepage = 'https://www.frontiersin.org'
WHERE (homepage IS NULL OR trim(homepage) = '') AND name ILIKE '%Frontiers%';

-- MDPI
UPDATE scholar.venue
SET homepage = 'https://www.mdpi.com'
WHERE (homepage IS NULL OR trim(homepage) = '') AND name ILIKE '%MDPI%';

-- Taylor & Francis
UPDATE scholar.venue
SET homepage = 'https://www.tandfonline.com'
WHERE (homepage IS NULL OR trim(homepage) = '') AND (name ILIKE '%Taylor & Francis%' OR name ILIKE '%Taylor and Francis%' OR name ILIKE '%T&F%');

-- SAGE
UPDATE scholar.venue
SET homepage = 'https://journals.sagepub.com'
WHERE (homepage IS NULL OR trim(homepage) = '') AND name ILIKE '%SAGE%';

-- Hindawi
UPDATE scholar.venue
SET homepage = 'https://www.hindawi.com'
WHERE (homepage IS NULL OR trim(homepage) = '') AND name ILIKE '%Hindawi%';

-- Oxford University Press
UPDATE scholar.venue
SET homepage = 'https://academic.oup.com'
WHERE (homepage IS NULL OR trim(homepage) = '') AND (name ILIKE '%Oxford University Press%' OR name ILIKE '%OUP%');

-- Cambridge University Press
UPDATE scholar.venue
SET homepage = 'https://www.cambridge.org'
WHERE (homepage IS NULL OR trim(homepage) = '') AND (name ILIKE '%Cambridge University Press%' OR name ILIKE '%CUP%');

-- Royal Society / RSP
UPDATE scholar.venue
SET homepage = 'https://royalsocietypublishing.org'
WHERE (homepage IS NULL OR trim(homepage) = '') AND (name ILIKE '%Royal Society%');

-- IOP Publishing
UPDATE scholar.venue
SET homepage = 'https://iopscience.iop.org'
WHERE (homepage IS NULL OR trim(homepage) = '') AND (name ILIKE '%IOP%');

-- APS (American Physical Society)
UPDATE scholar.venue
SET homepage = 'https://journals.aps.org'
WHERE (homepage IS NULL OR trim(homepage) = '') AND (name ILIKE '%APS%' OR name ILIKE '%American Physical Society%');

-- ACS (American Chemical Society)
UPDATE scholar.venue
SET homepage = 'https://pubs.acs.org'
WHERE (homepage IS NULL OR trim(homepage) = '') AND (name ILIKE '%ACS%' OR name ILIKE '%American Chemical Society%');

-- RSC (Royal Society of Chemistry)
UPDATE scholar.venue
SET homepage = 'https://pubs.rsc.org'
WHERE (homepage IS NULL OR trim(homepage) = '') AND (name ILIKE '%RSC%' OR name ILIKE '%Royal Society of Chemistry%');

-- AAAS / Science
UPDATE scholar.venue
SET homepage = 'https://www.science.org'
WHERE (homepage IS NULL OR trim(homepage) = '') AND (name ILIKE '%AAAS%' OR name ILIKE '%Science%');

-- Cell Press
UPDATE scholar.venue
SET homepage = 'https://www.cell.com'
WHERE (homepage IS NULL OR trim(homepage) = '') AND (name ILIKE '%Cell Press%' OR name ILIKE '%Cell%');

-- Karger
UPDATE scholar.venue
SET homepage = 'https://www.karger.com'
WHERE (homepage IS NULL OR trim(homepage) = '') AND name ILIKE '%Karger%';

-- De Gruyter
UPDATE scholar.venue
SET homepage = 'https://www.degruyter.com'
WHERE (homepage IS NULL OR trim(homepage) = '') AND name ILIKE '%De Gruyter%';

-- SPIE
UPDATE scholar.venue
SET homepage = 'https://www.spiedigitallibrary.org'
WHERE (homepage IS NULL OR trim(homepage) = '') AND name ILIKE '%SPIE%';

-- SIAM
UPDATE scholar.venue
SET homepage = 'https://www.siam.org/publications/siam-journals'
WHERE (homepage IS NULL OR trim(homepage) = '') AND name ILIKE '%SIAM%';

-- ASME
UPDATE scholar.venue
SET homepage = 'https://asmedigitalcollection.asme.org'
WHERE (homepage IS NULL OR trim(homepage) = '') AND name ILIKE '%ASME%';

-- AIP
UPDATE scholar.venue
SET homepage = 'https://aip.scitation.org'
WHERE (homepage IS NULL OR trim(homepage) = '') AND name ILIKE '%AIP%';























