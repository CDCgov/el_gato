# Known Problematic Alleles
el_gato demonstrates a better ability to correctly call STs for *L. pneumophila* compared to other tools available, especially regarding the *mompS* gene duplication. However, el_gato still is not 100% accurate. For example, when the *mompS* alleles 7 and 15 are identified as possible options for an isolate (e.g., ERR8122877), el_gato cannot differentiate between the two alleles to determine the primary allele even with read lengths of 250 base pairs (bp). This inability to distinguish between *mompS* alleles 7 and 15 is due to the distance between the biallelic SNP and the reverse primer. The biallelic SNP for these two alleles is located at position 429 in the *L. pneumophila* Paris genome, while the position of the diagnostic primer spans positions 940 - 960 bp. As a result, reads would need to span 511 bp to differentiate between the two possible alleles. It is likely that there are other alleles than those listed below for which a similar difficulty in calling the primary *mompS* allele will arise.

### Table listing known alleles that el_gato can not differenatiate between
gene | allele numbers | NCBI example
-----|----------------|--------
*mompS* | 7 and 15 | ERR8122877
*mompS* | 28 and Novel Allele Type | SRR23514483