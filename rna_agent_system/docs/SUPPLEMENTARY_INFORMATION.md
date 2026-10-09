# Supplementary information

**A multi-agent system for RNA design with capability-gated prediction and constraint-navigated generation**


## Table of Contents

**Supplementary Notes**

- Supplementary Note 1. Output quality and completion of the remaining workflows
- Supplementary Note 2. IRES prediction on the validated anchor set
- Supplementary Note 3. Advisory review and per-agent ablation in the multi-agent layer

**Supplementary Methods**

- M1. Claim-overreach audit sets and gating conditions
- M2. Pre-registered constraint matrices and budget matching
- M3. The evidence-based two-step full-length mRNA design
- M4. Baselines and budgets
- M5. Ablation configurations of the multi-agent layer

**Supplementary Figures**

- Supplementary Fig. S1. Candidate validity in tertiary-structure inverse folding
- Supplementary Fig. S2. Scoring direction on vaccine and wild-type sequences
- Supplementary Fig. S3. IRES prediction screening on the validated anchor set
- Supplementary Fig. S4. Aptamer constraint navigation across quota levels
- Supplementary Fig. S5. Advisory review leaves outcomes unchanged across its three conditions
- Supplementary Fig. S6. Model calls per campaign

**Supplementary Tables**

- Supplementary Table S1. The eleven domain workflows
- Supplementary Table S2. The forty-one scientific tools
- Supplementary Table S3. Representative ungated claims and their gated versions
- Supplementary Table S4. Results by reference for tertiary-structure inverse folding

**References**

## Supplementary Notes

### Supplementary Note 1. Output quality and completion of the remaining workflows

#### S1.1 RNA aptamer design

This workflow's results are in the main text (Fig. 5e–g). The structure-based predictors this workflow needs for affinity validation, EGARPS+ native probability, ProteinX interface confidence (ipTM) and RhoFold mean per-residue confidence (pLDDT), showed no reliable screening, ranking or docking power in any predictor–target combination when profiled on verified anchor sets (main-text Fig. 3a–d). Ranking and claims therefore exclude the decertified predictors rather than presenting their outputs as affinity evidence. All 18 aptamer benchmark tasks succeed (Fig. 2a).

#### S1.2 RNA tertiary-structure inverse folding

The 20 benchmark tasks produced 73 candidates, each with four complete quality metrics, refold confidence (mean pLDDT), alignment root-mean-square deviation (RMSD), alignment template-modelling (TM) score and recovery rate. Each candidate is graded against its task's registered pass criteria. The baseline task (1EHZ) requires refold mean pLDDT of at least 70 and RMSD of at most 2.0 Å, the two large-reference tasks (1GID and 1HR2) at least 65 and at most 3.0 Å, and the remaining seventeen tool-configuration tasks at least 65 with no RMSD gate.

31 of the 73 candidates reach the pLDDT threshold, and 1 of the 14 RMSD-gated candidates meets its RMSD bound (Supplementary Fig. S1). The lowest RMSD is 2.49 Å. 12 of the 20 tasks deliver at least one passing candidate. Across all 73 candidates, the medians are pLDDT 37.4 (range 24.6–84.0), RMSD 18.8 Å (2.5–28.4), TM-score 0.025 and sequence recovery 0.690 (0.439–1.0). Results for each of the eight Protein Data Bank (PDB) references appear in Supplementary Table S4.

The designed sequences differ from the reference sequence (median recovery 0.69), so refold RMSD is a bound on inverse-folding fidelity rather than a measure of sequence recovery. The generators propose new sequences for the target structure rather than reproduce the native chain. Among the 30 designs of 154 nucleotides (nt) or longer, the 23 from RhoDesign refold at pLDDT 24.6–29.1, while the 7 from RiboDiffusion, 158-nt designs against the two Tetrahymena references, refold at pLDDT 70.0–70.7. Among the 43 shorter designs, 24 reach the pLDDT threshold, the hammerhead ribozyme accounting for 18 of the 19 exceptions. All 20 tasks complete end-to-end (Fig. 2a).

#### S1.3 mRNA sequence scoring

The mRNA scoring workflow (GC content, LinearFold minimum free energy (MFE) and codon adaptation index (CAI), total score = −MFE + codons · log(CAI)) is validated on vaccine and wild-type sequences through the deployed tools. All 222 sequences were scored, with zero failures. The sequences are the two vaccine CDSs (BNT162b2 and mRNA-1273), the 20 wild-type (WT) RefSeq CDSs of the 20-target full-length mRNA set, and 10 synonymous resamples of each wild type, with the same generator and seeds as the Fig. 2b,c control. The CAI species is Homo sapiens for all conditions.

The wild-type total score exceeds the median of its 10 random synonymous resamples on 15 of 20 targets and exceeds all 10 on 12 of 20 (two-sided sign P = 0.041; Supplementary Fig. S2). The 20 wild-type CDSs reach a higher median total score than the 200 resamples (P = 6.2 × 10⁻³, δ = 0.37), as do the two vaccine CDSs (P = 9.9 × 10⁻⁵, δ = 1.0) and all 22 combined (P = 9.7 × 10⁻⁴, δ = 0.43). The two vaccine CDSs both score higher than the 10 Spike-WT resamples (P = 0.030, δ = 1.0), with BNT162b2 at 260.7 and mRNA-1273 at 404.8 against the resamples' −373.4 to −277.1.

Wild type and random differ in CAI (wild-type median 0.725, random 0.680, P = 1.5 × 10⁻⁷, δ = 0.71) but not in folding energy per nucleotide, as in Fig. 2b,c. The vaccine CDSs lead on both components (CAI 0.952 and 0.979, MFE per nucleotide −0.085 and −0.113 compared with random, P = 3.9 × 10⁻⁴, δ = −0.99). All 13 scoring tasks succeed (Fig. 2a).

#### S1.4 sgRNA design

The sgRNA workflow's two quality predictors, CRGPT handle efficiency and CRISOT off-target, have no labelled anchor set. Both predictors are therefore unprofiled, and the DecisionGate records require-profiling verdicts for them (Fig. 4h, CRGPT 244 and CRISOT 25). This workflow makes no claim of biological validity. All 30 benchmark tasks succeed end-to-end (Fig. 2a).

#### S1.5 ASO target screening

ASO target screening is a thermodynamic screen built on the ViennaRNA tools (RNAplfold site accessibility and RNAup/RNAcofold duplex hybridization energies). Its validity is that of the published thermodynamics, and no learned predictor is involved, so no capability profiling is required. All 14 benchmark tasks succeed end-to-end (Fig. 2a).

### Supplementary Note 2. IRES prediction on the validated anchor set

The internal ribosome entry site (IRES) prediction workflow was evaluated on the IRES anchor set. The set contains nine validated IRES elements (six viral, three cellular) and 50 random human 5′UTR sequences as negatives. The workflow ran with its default settings except that the labelling threshold was set to zero so that raw scores were returned. All 59 sequences were scored, with zero failures.

The pre-registered primary analysis (mode 0, full sequence) gives an area under the receiver operating characteristic curve (AUROC) of 0.478 (95% confidence interval (CI) 0.311–0.649; two-sided Mann–Whitney P = 0.841; Cliff's δ = −0.04), with the interval spanning chance. The sliding-window analysis (mode 2, 174-nt window, 50-nt step), disclosed as post-hoc, reaches an AUROC of 0.673 (95% CI 0.467–0.862; P = 0.102; δ = 0.35). Both analyses fall below the 0.8 screening gate encoded in this predictor's capability profile (Supplementary Fig. S3). Across the 241-run production campaign, the DecisionGate recorded 24 verdicts for IRESfinder, all rejects of screening plans (Fig. 4h).

### Supplementary Note 3. Advisory review and per-agent ablation in the multi-agent layer

The multi-agent layer was evaluated in two experiments. Across the 31-session process-aware benchmark, every session completed and succeeded (Supplementary Fig. S5). In the advisory experiment's third condition, the review model was made unreachable on purpose, so every review call failed and was recorded in the audit trail. The per-agent ablation (Supplementary Methods M5) ran the same benchmark with advisory review off and retries off, each in its own condition, and every session succeeded with unchanged per-turn outcomes. On two multi-step pipelines, the agent layer left the workflow outcomes unchanged. The ClaimGate rejected five of the twelve claims drafted by the synthesis agent's large language model (LLM) report, all based on unprofiled predictors. Model calls per campaign appear in Supplementary Fig. S6.

## Supplementary Methods

### M1. Claim-overreach audit sets and gating conditions

The 45-task aptamer claim-overreach audit set comprises 24 tasks with exactly recomputable ground truth and 21 untrusted-predictor ranking and screening tasks spanning all anchor targets. The ungated condition makes exactly two LLM calls per task at temperature 0, one to plan the analyses and one to draft the report. The gated condition runs the same tasks through the gates, with the agent's reported metrics verified by exact recomputation before release.

The mRNA claim-overreach audit set is built on targets of the 20-target full-length mRNA set, GenNav-λ CDS candidates and the full-length workflow's top three mRNAs per target. The ten deterministic tasks concern the CDS candidates, and their ground truth is recomputed CAI on the target's Kazusa table, folding energy via LinearFold and the constraint checks. The other ten tasks are scored by the two GEMORNA expression predictors, 3′UTR stability and mean ribosome load (MRL), and a junction metric that sums the MFE per nucleotide in the 5′UTR–CDS junction window and the energy change from constrained folding. The gated condition runs the same tasks through the gates under the default capability map (the certified GEMORNA-MRL profile).

The expression predictor was profiled on the measured ribosome-load anchors of a published massively parallel translation assay. It predicted a ribosome load for every anchor, and the comparison with the measured values under the pre-registered thresholds determined its screening and ranking grades (Fig. 4a). The decision matrix (Fig. 4b) tests gating on both GEMORNA expression predictors in twelve pre-registered combinations, six DecisionGate requests, three ClaimGate claims and three tool-execution checks, over the three certified anchor libraries and an unprofiled anchor set from the mRNA audit set. Each combination was executed under the default capability map with the gates on, producing all three verdicts, allow, downgrade and block.

Every comparative experiment was pre-registered and preceded by a pilot with a decisive control condition. Negative pilots were retained as evidence. The budget-matching rule applied to every comparative campaign. For any comparison based on a pool's best candidate or on the size of the region dominated by its Pareto frontier, the conditions generated and evaluated the same total number of candidates. In every paired experiment, the prompts, the model and the predictor services were the same in both conditions, and all claims were judged together by one set of fixed rules.

### M2. Pre-registered constraint matrices and budget matching

The mRNA constraint matrix requires GC content between 30% and 80% in every 100-nucleotide sliding window of the full construct, homopolymer runs below 14 nucleotides, a longest stem of at most 12 base pairs in the initiation region (the 5′UTR plus the first 30 nucleotides of the CDS), a longest stem of at most 30 base pairs over the full construct, GC content between 20% and 80% in the two 60-nucleotide windows centred on the 5′UTR–CDS and CDS–3′UTR junctions, and CAI ≥ 0.8. The aptamer constraint matrix sets per profile a length range (compact 25–34, standard 40–55 and extended 61–80 nucleotides), a GC window (42–62%, 40–65% and 35–60%), a limit on homopolymer runs (below 5, below 5 and below 6 nucleotides) and on the longest stem (at most 7, 9 and 12 base pairs), and requires that any two of the five candidates delivered for a profile differ in at least 15% of their sequence.

The selection-step attempt of Fig. 5a used one fixed candidate pool for each of the five targets. Per target, LinearDesign at four λ settings (0, 1, 4 and 10) plus one RNARL run and 30 GEMORNA CDS samples yield 35 CDS candidates. Each CDS is crossed with 9 GEMORNA UTR combinations, and the pool is filtered through the deployed tools against the pre-registered mRNA constraint matrix. Passing candidates are delivered for each of the three profiles, and every delivered batch must meet the 2% diversity threshold.

The mRNA and aptamer campaigns of Fig. 5b–g compared navigation against the static condition at matched budgets. Eleven targets entered through the user form and appear in no other dataset. The five human therapeutic proteins were designed through GenNav-λ within a generation budget of 35, and the six aptamer targets were designed through a grid of ODesign lengths, seeds and samples within a generation budget of 48, three of them on existing ProteinX folds of the same sequences. The static condition for these targets was completed at the same matched budgets. For the five mRNA targets, the static condition generated the same fixed candidate pool as the selection-step attempt, and the navigation candidates from the form sessions were evaluated under the same constraint matrix and ranking. For the six aptamer targets, the static condition used the same structures and deterministic binding hotspots as in navigation. The budget sweep compared navigation against the static condition at each quota on the 39-target pool (Supplementary Fig. S4).

### M3. The evidence-based two-step full-length mRNA design

The full-length mRNA workflow designs each mRNA in two evidence-based steps. Step 1 selects coding sequences. Every CDS delivered by the CDS workflow is evaluated once, at most one CDS per navigation profile is retained (the static condition keeps the top three), and selection ranks by the shared CDS combined score, with UTR samples never resampled per CDS so that CDS ranking cannot be confounded by UTR sampling variance. Step 2 pairs the selected CDSs with one UTR pool per run, twelve generated 5′UTRs and ten generated 3′UTRs (the generative model's published screening scale) plus a benchmark pool of the BNT162b2 UTR pair (the 51-nucleotide α-globin-derived 5′UTR and the 94-nucleotide AES–mtRNR1 3′UTR), the LinearDesign paper's 5′UTR and the natural human HBA1 pair. The pool is filtered by rules with citable quantitative thresholds only. No upstream AUG is allowed in a designed 5′UTR (the uAUG penalty being the strongest negative feature of the ribosome-load model whose assay certifies the MRL predictor). No class-II tandem-AUUUA AU-rich element is allowed in a 3′UTR (the classical instability-element classification). Two Kozak structure gates apply to the assembled mRNA, with the 5′-terminal 60-nucleotide window not folding at or below −30 kcal/mol (a −30 hairpin 12 nucleotides from the cap prevents 40S subunit engagement whereas the same hairpin 52 nucleotides from the cap has no effect) and no 150-nucleotide window through the AUG context folding at or below −61 kcal/mol (the hp7 scanning-stall threshold). Rules without an established quantitative threshold in the literature, overall U-content limits, GU-rich innate-immune motif counts and internal polyadenylation-signal screens, were deliberately not implemented. The remaining 5′UTRs are ranked by the certified ribosome-load predictor, so a generated UTR is selected only when it outranks the benchmarks. The 3′UTR-stability predictor, which has no profiling evidence under any registered task type, was moved from a ranking objective to a report-only diagnostic. The final mRNA is 5′UTR + CDS + 3′UTR, with capping and polyadenylation left to the wet lab.

### M4. Baselines and budgets

Two baselines, a bare model and a same-tool loop, were compared against the system on the 31-session process-aware benchmark (Fig. 6). The bare model makes exactly one model call per turn under zero-shot and few-shot prompting (the few-shot examples demonstrate the output format only). The same-tool loop is a ReAct-style loop driving the same 41 tools through the same executor (the same advisory policy as the system), plus a single file-writing command, because every tool takes file inputs that the system's workflows create internally. Its model-call budgets take three levels. The system-matched budget equals the system's measured per-session model-call count, and the other two are 3× and 10× of it. The session budget is allocated evenly across turns, and the candidate-generation budget equals the system's evaluated-candidate count at every level.

The system and both baselines were judged by the same fixed rules. Each workflow's validity checks are recomputed exactly (length and alphabet, translation identity, target complementarity or antisense ancestry, window substring, PDB parseability, fold-back against the target dot-bracket). Delivered quality on the two structure tasks must match or beat the system's best on the same turn, and a deliverable that is one of the task's input files is rejected. Claim verdicts follow the blind adjudication rules, and every recomputable metric is verified exactly. Claims based only on an unprofiled predictor are judged unverifiable for all three. The evaluation workflows are judged on output format alone, and a complete negative answer (no regions above threshold) counts as delivered for all three.

### M5. Ablation configurations of the multi-agent layer

To test the function of each agent, ablation experiments were performed on the multi-agent layer. The full 31-session process-aware benchmark was run in three conditions, the production default, advisory review off and retries off. Two multi-step pipelines, tertiary-structure inverse folding and diffusion aptamer design, each feed their best candidate into the small-molecule interaction workflow. Each ran in three configurations, the production command-line interface, the same interface with the synthesis LLM off and sequential node execution with no agent layer. The three benchmark conditions made 218 advisory review calls, 146 in the production default, 0 with review off and 72 with retries off. The full configuration made all four calls to the synthesis LLM, one per pipeline to draft the report and one to extract its claims, and the other two made none.

## Supplementary Figures

### Supplementary Fig. S1. Candidate validity in tertiary-structure inverse folding

Each of the 73 candidates from the 20 tertiary-structure tasks appears as one dot in each of two panels per reference, one showing refold confidence (mean pLDDT) and the other alignment RMSD, with a filled dot marking a pass.


### Supplementary Fig. S2. Scoring direction on vaccine and wild-type sequences

Each target occupies one row, in which open dots show the ten random synonymous resamples, a vertical line marks their median, and the filled dot is the wild type. Rows are sorted by the wild type's difference from its own median, in descending order.


### Supplementary Fig. S3. IRES prediction screening on the validated anchor set

The receiver operating characteristic analysis of the IRES prediction workflow on the validated anchor set.


### Supplementary Fig. S4. Aptamer constraint navigation across quota levels

Navigation is compared against the static condition on the 39-target pool, with delivered pairs shown against the quota of raw candidates per target. Each target is designed under three profiles, so the 39 targets yield 117 pairs. Point values are each condition's total delivered pairs. The ratio under each quota counts pairs delivered by navigation only : by the static condition only.


### Supplementary Fig. S5. Advisory review leaves outcomes unchanged across its three conditions

The advisory review grid of the 31-session process-aware benchmark, one row per session in three condition blocks, review off, review on and review on with all review calls made to fail.


### Supplementary Fig. S6. Model calls per campaign

Each campaign appears as one row of circles. The claim-overreach campaigns make two calls per task, while the decision matrix and the navigation campaigns make none. The production campaign (the system's routine runs) makes two per reviewed turn, and the navigation runs of the 11 sessions made 22 calls.


## Supplementary Tables

### Supplementary Table S1. The eleven domain workflows

| Workflow | Function | Generation and evaluation | Ranking | Quality review |
|---|---|---|---|---|
| mRNA CDS design | Redesign the coding sequence | LinearDesign, RNARL and GEMORNA; GC, folding energy, codon adaptation | −MFE + codons·log(CAI) | Advisory |
| Full-length mRNA design | Design each mRNA, 5′UTR + CDS + 3′UTR | Two evidence-based steps (Supplementary Methods M3), CDS selection then UTR pools filtered by literature-threshold rules | Achievement scalarizing function (ASF) | Advisory |
| mRNA sequence scoring | Score existing sequences | LinearFold MFE, GC content, codon adaptation | −MFE + codons·log(CAI) | None |
| siRNA design | Design guides with off-target safety | Evitar or sliding windows; duplex MFE, end asymmetry, off-target scan | ASF on duplex efficiency, specificity and antisense-loading asymmetry | Advisory |
| sgRNA design | Design sgRNA handles from a seed | CRGPT generation and re-scoring, optional CRISOT off-target | ASF on handle score and specificity | Advisory |
| ASO target screening | Find accessible antisense target sites | RNAplfold accessibility, 15–20-nucleotide window, RNAup and RNAcofold hybridization | ASF on site accessibility and binding free energy | None |
| IRES prediction | Find internal ribosome entry sites | IRESfinder, full-sequence, fragment and sliding-window modes, structural context as metadata | IRES probability | Advisory |
| RNA aptamer design | Design aptamers against a protein | Hotspot identification, ODesign, two-stage evaluation (refold confidence, then complex prediction and scoring) | ASF on complex probability, fold confidence and interface score | Advisory |
| RNA secondary-structure inverse folding | Fold to a target secondary structure | RNAinverse repeat sampling, GC content, RNAfold validation | Structure distance per nucleotide (0 = exact) | Advisory |
| RNA tertiary-structure inverse folding | Design for a target 3D structure | RhoDesign, RiboDiffusion; refold confidence, RMSD, TM-score | ASF on refold confidence and reference closeness | Advisory |
| RNA–small-molecule interaction | Predict RNA–ligand binding propensity | RNAsmol and GerNA-Bind, averaged | Binding probability | None |

### Supplementary Table S2. The forty-one scientific tools

All tools except those marked System implementation are served by local microservices (Methods). The CapGate column marks the predictors reviewed by the decision gate, with "pending" denoting the absence of a labelled anchor set (Supplementary Note 1, section S1.4).

| Tool (registered name) | Class | Method | Function | CapGate | Ref. |
|---|---|---|---|---|---|
| `predict_rna_secondary_structure` | Compute | ViennaRNA RNAfold | MFE secondary structure | — | [1], [2] |
| `predict_rna_secondary_structure_with_linearfold` | Compute | LinearFold | Secondary structure prediction | — | [3] |
| `inverse_fold_rna_secondary_structure_vienna` | Generator | ViennaRNA RNAinverse | Secondary-structure inverse folding | — | [2] |
| `compute_sirna_duplex_binding_vienna` | Compute | ViennaRNA RNAcofold | Duplex MFE and end asymmetry | — | [2], [4]–[6] |
| `compute_rna_rna_interaction_vienna` | Compute | ViennaRNA RNAup | RNA–RNA interaction energy | — | [7] |
| `compute_aso_target_accessibility_vienna` | Compute | ViennaRNA RNAplfold | ASO site accessibility | — | [8] |
| `predict_rna_local_accessibility_profile_vienna` | Compute | ViennaRNA RNAplfold | Per-position accessibility | — | [8] |
| `design_mrna_cds_with_lineardesign` | Generator | LinearDesign | Protein-to-CDS design | — | [9] |
| `design_mrna_cds_with_rnarl` | Generator | RNARL | Protein-to-CDS generation | — | [10] |
| `design_mrna_cds_with_gemorna` | Generator | GEMORNA | Protein-to-CDS generation | — | [11] |
| `design_5utr_with_gemorna` | Generator | GEMORNA | 5′UTR generation | — | [11] |
| `design_3utr_with_gemorna` | Generator | GEMORNA | 3′UTR generation | — | [11] |
| `predict_5utr_mrl_with_gemorna` | Predictor | GEMORNA MRL model | Predicted 5′UTR ribosome load | Enforced | [11] |
| `predict_3utr_stability_with_gemorna` | Predictor | GEMORNA 3′UTR-stability model | Predicted 3′UTR stability, report-only | Enforced | [11] |
| `predict_mrna_stability_with_rnastop` | Predictor | RNASTOP | mRNA stability prediction | Enforced | [12] |
| `predict_rna_tertiary_structure_with_rhofold` | Predictor | RhoFold+ | RNA 3D structure prediction | Enforced | [13] |
| `design_rna_sequence_with_rhodesign` | Generator | RhoDesign | Structure-to-sequence inverse folding | — | [14] |
| `design_rna_inverse_fold_with_ribodiffusion` | Generator | RiboDiffusion | Inverse folding by diffusion | — | [15] |
| `score_structure_alignment` | Compute | System implementation (Biopython, TM-score) | RMSD and TM-score | — | [16], [17] |
| `score_rna_ligand_binding_with_rnasmol` | Predictor | RNAsmol | RNA–ligand binding probability | Enforced | [18] |
| `score_rna_ligand_binding_with_gernabind` | Predictor | GerNA-Bind | RNA–ligand binding probability | Enforced | [19] |
| `predict_rna_protein_complex_with_proteinx` | Predictor | Protenix | Complex prediction, interface confidence | Enforced | [20], [21] |
| `predict_protein_structure_with_proteinx` | Predictor | Protenix | Protein 3D structure prediction | — | [20], [21] |
| `score_rna_protein_complex_with_egarps` | Predictor | EGARPS+ | Complex scoring, native-like probability | Enforced | [22] |
| `analyze_rna_protein_interface` | Compute | System implementation (FreeSASA, Biopython) | Interface contacts, buried area | — | [17], [23] |
| `score_crispr_off_target_with_crisot` | Predictor | CRISOT-Score | sgRNA off-target propensity | Pending | [24] |
| `calculate_crispr_specificity_with_crisot` | Compute | CRISOT-Spec | Genome-wide specificity summary | — | [24] |
| `design_sgrna_handle_with_crgpt` | Generator | CRGPT | Handle generation from seed | — | [25] |
| `score_sgrna_handle_with_crgpt` | Predictor | CRGPT | Handle re-scoring | Pending | [25] |
| `design_sirna_with_evitar` | Generator | Evitar | siRNA and Cas13 guide design | — | [26] |
| `run_blastn_similarity_search` | Compute | NCBI BLAST+ | Nucleotide similarity search | — | [27] |
| `run_bowtie2_short_alignment` | Compute | Bowtie2 | Short-sequence alignment | — | [28] |
| `compute_rna_sequence_gc_content` | Compute | RNA sequence metrics service | GC fraction | — | — |
| `compute_rna_sequence_u_content` | Compute | RNA sequence metrics service | U fraction | — | — |
| `compute_dot_bracket_unpaired_fraction` | Compute | RNA sequence metrics service | Unpaired-base fraction | — | — |
| `compute_cai_for_cds_sequence` | Compute | System implementation (Sharp–Li, Kazusa) | Codon adaptation index, 11 species | — | [29], [30] |
| `identify_protein_binding_hotspots` | Compute | System implementation (FreeSASA, DBSCAN) | Surface binding-hotspot residues | — | [23], [31] |
| `build_odesign_aptamer_input_json` | Utility | System implementation | ODesign input serialization | — | — |
| `run_odesign_inference` | Generator | ODesign | Generative binding-RNA design | — | [32] |
| `extract_rna_sequence_from_cif` | Utility | System implementation (Biopython) | RNA extraction from mmCIF | — | [17] |
| `predict_putative_ires_with_iresfinder` | Predictor | IRESfinder | Putative IRES scoring | Enforced | [33] |

### Supplementary Table S3. Representative ungated claims and their gated versions

Each row summarizes one task of the paired gating experiments of Fig. 4d–g, with verdict labels as in Fig. 4e,g. The aptamer ground truth is the anchors' measured dissociation constant (Kd), and verbatim claim, adjudication and gate texts remain in the frozen per-claim records.

| Task (audit group) | Ungated condition, claim and verdict | Gated condition, outcome and verdict | Gate action |
|---|---|---|---|
| Aptamer ranking, Angiopoietin-2 (untrusted-predictor task) | Claimed the best binder by structure-predictor scores, a **false positive** against the Kd truth | Structure-predictor ranking rejected, a GC-proxy substitute claim rejected, no claim published | Unprofiled predictor, substitute a certified predictor or downgrade the claim |
| Aptamer screening, Angiopoietin-2 (untrusted-predictor task) | Claimed no candidate binds, a **false positive**, two anchors bind | Screening requests rejected, no claim published | Unprofiled predictor, same verdict for all three predictors |
| Aptamer ranking, Thrombin (untrusted-predictor task) | Claimed the top-ranked candidate best, a **false positive** | Published an abstention instead, adjudicated **borderline** | Ranking rejected, the abstention passed as deterministic content |
| Aptamer ranking, VEGF (untrusted-predictor task) | Three per-predictor best-candidate claims, all **false positives** | One request allowed for annotation use only, its confidence claim rejected, no claim published | Unprofiled predictors |
| Deterministic GC target (deterministic task) | Claimed a GC content of 0.60, **true positive**, verified | Retained the same claim, **true positive**, verified | Deterministic content, no predictor dependencies |
| Deterministic GC target (deterministic task) | Claimed a GC content of 0.60, **true positive**, verified | **Suppressed** for declaring an unprofiled dependency | Dependency never profiled |
| mRNA 3′UTR-stability ranking, EPO (untrusted-predictor task) | Claimed the highest-stability candidate, a **false positive** with no certified basis | Ranking blocked, the no-selection statement rejected, no claim published | No ranking profiling for this target family |
| mRNA 5′UTR ribosome-load optimum (certified-predictor task) | Claimed the highest-expression 5′UTR, a **false positive** | Passed both gates and stayed false, the single surviving **false positive** | Verified ranking power on the certified library |

### Supplementary Table S4. Results by reference for tertiary-structure inverse folding

Candidate counts and quality medians for the eight reference structures of the 20 tasks.

| PDB | Reference | Candidates | Pass | pLDDT median | RMSD median (Å) |
|-----|-----------|--------|------|-----------|---------------|
| 1F7U | tRNA-Arg (yeast) | 14 | 14 | 82.6 | 21.2 |
| 1EHZ | tRNA-Phe (yeast) | 5 | 4 | 79.0 | 21.0 |
| 1Y26 | Adenine riboswitch | 2 | 2 | 75.2 | 3.4 |
| 1GID | Group I intron P4-P6 domain | 12 | 2 | 28.3 | 20.0 |
| 1HR2 | Group I intron P4-P6 domain (DelC209) | 11 | 3 | 27.4 | 23.7 |
| 2GDI | TPP riboswitch | 7 | 2 | 26.6 | 18.8 |
| 3D2V | TPP riboswitch (eukaryotic) | 4 | 1 | 27.7 | 17.8 |
| 1MME | Hammerhead ribozyme | 18 | 0 | 36.3 | 9.7 |

## References

The numbered references are cited from the Ref. column of Supplementary Table S2.

1. Lorenz, R. et al. ViennaRNA Package 2.0. *Algorithms Mol. Biol.* **6**, 26 (2011).
2. Hofacker, I. L. et al. Fast folding and comparison of RNA secondary structures. *Monatsh. Chem.* **125**, 167–188 (1994).
3. Huang, L. et al. LinearFold: linear-time approximate RNA folding by 5′-to-3′ dynamic programming and beam search. *Bioinformatics* **35**, i295–i304 (2019).
4. Bernhart, S. H. et al. Partition function and base pairing probabilities of RNA heterodimers. *Algorithms Mol. Biol.* **1**, 3 (2006).
5. Khvorova, A., Reynolds, A. & Jayasena, S. D. Functional siRNAs and miRNAs exhibit strand bias. *Cell* **115**, 209–216 (2003).
6. Schwarz, D. S. et al. Asymmetry in the assembly of the RNAi enzyme complex. *Cell* **115**, 199–208 (2003).
7. Mückstein, U. et al. Thermodynamics of RNA–RNA binding. *Bioinformatics* **22**, 1177–1182 (2006).
8. Bernhart, S. H., Hofacker, I. L. & Stadler, P. F. Local RNA base pairing probabilities in large sequences. *Bioinformatics* **22**, 614–615 (2006).
9. Zhang, H. et al. Algorithm for optimized mRNA design improves stability and immunogenicity. *Nature* **621**, 396–403 (2023).
10. RNARL: RNA design via reinforcement learning. Software at https://github.com/ShenggengLin/RNARL (2025).
11. Zhang, H. et al. Deep generative models design mRNA sequences with enhanced translational capacity and stability. *Science* **390**, eadr8470 (2025).
12. RNASTOP: prediction and optimization of mRNA stability by integrating deep learning and thermodynamic property-guided heuristic search. Software at https://github.com/ShenggengLin/RNASTOP (2025).
13. Shen, T. et al. Accurate RNA 3D structure prediction using a language model-based deep learning approach. *Nat. Methods* **21**, 2287–2298 (2024).
14. Wong, F. et al. Deep generative design of RNA aptamers using structural predictions. *Nat. Comput. Sci.* **4**, 829–839 (2024).
15. Huang, H., Lin, Z., He, D., Hong, L. & Li, Y. RiboDiffusion: tertiary structure-based RNA inverse folding with generative diffusion models. *Bioinformatics* **40**, i347–i356 (2024).
16. Zhang, Y. & Skolnick, J. Scoring function for automated assessment of protein structure template quality. *Proteins* **57**, 702–710 (2004).
17. Cock, P. J. A. et al. Biopython: freely available Python tools for computational molecular biology and bioinformatics. *Bioinformatics* **25**, 1422–1423 (2009).
18. Ma, H. et al. RNA–ligand interaction scoring via data perturbation and augmentation modeling. *Nat. Comput. Sci.* **5**, 648–660 (2025).
19. Xia, Y. et al. Deciphering RNA–ligand binding specificity with GerNA-Bind. *Nat. Mach. Intell.* **7**, 1996–2008 (2025).
20. Chen, X. et al. Protenix: advancing structure prediction through a comprehensive AlphaFold3 reproduction. Preprint at bioRxiv https://doi.org/10.1101/2025.01.08.631967 (2025).
21. Abramson, J. et al. Accurate structure prediction of biomolecular interactions with AlphaFold 3. *Nature* **630**, 493–500 (2024).
22. Jiang, Z., Zhang, Y., Yang, G. & Liu, R. Graph learning-based scoring of RNA–protein complex structures. *J. Chem. Theory Comput.* **21**, 9200–9213 (2025).
23. Mitternacht, S. FreeSASA: an open source C library for solvent accessible surface area calculations. *F1000Research* **5**, 189 (2016).
24. Chen, Q. et al. Genome-wide CRISPR off-target prediction and optimization using RNA–DNA interaction fingerprints. *Nat. Commun.* **14**, 7521 (2023).
25. sgrna_design: sgRNA handle design (CRGPT). Software at https://github.com/bitguolab/sgrna_design (unpublished).
26. Zhang, D., Tian, J., Wang, Y. & Lu, J. Evitar: designing anti-viral RNA therapies against future RNA viruses. *Bioinformatics* **38**, 2437–2443 (2022).
27. Camacho, C. et al. BLAST+: architecture and applications. *BMC Bioinformatics* **10**, 421 (2009).
28. Langmead, B. & Salzberg, S. L. Fast gapped-read alignment with Bowtie 2. *Nat. Methods* **9**, 357–359 (2012).
29. Sharp, P. M. & Li, W.-H. The codon adaptation index—a measure of directional synonymous codon usage bias, and its potential applications. *Nucleic Acids Res.* **15**, 1281–1295 (1987).
30. Nakamura, Y., Gojobori, T. & Ikemura, T. Codon usage tabulated from international DNA sequence databases: status for the year 2000. *Nucleic Acids Res.* **28**, 292 (2000).
31. Ester, M., Kriegel, H.-P., Sander, J. & Xu, X. in *Proceedings of the Second International Conference on Knowledge Discovery and Data Mining (KDD-96)* (eds Simoudis, E., Han, J. & Fayyad, U. M.) 226–231 (AAAI Press, 1996).
32. Zhang, O. et al. ODesign: a world model for biomolecular interaction design. Preprint at arXiv https://doi.org/10.48550/arXiv.2510.22304 (2025).
33. Zhao, J. et al. IRESfinder: identifying RNA internal ribosome entry site in eukaryotic cell using framed k-mer features. *J. Genet. Genomics* **45**, 403–406 (2018).
