import json
import os

base = '/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system/data/benchmarks/RNA-BioBench-Platform/tasks/04_sirna_design'

def write(task_id, category, desc, inp, tools, rubric, source, ref=None):
    data = {
        'task_id': task_id,
        'workflow': 'sirna_design',
        'category': category,
        'description': desc,
        'input': inp,
        'expected_tool_chain': tools,
        'evaluation_rubric': rubric,
        'source': source,
        'paper_reference': ref,
    }
    fname = os.path.join(base, f'{task_id}.json')
    with open(fname, 'w') as f:
        json.dump(data, f, indent=2)
    print(f'Wrote {fname}')

fasta = 'data/references/species/sars_cov_2/virus_fragment_1k.fa'

# 019 predesign + multifapredsi
write('04_sirna_design_019_antiviral_predesign_multifapredsi', 'full',
      'Antiviral siRNA design with Evitar predesign mode and multifapredsi predictor',
      {'mode':'antiviral','target_fasta_path':fasta,'candidate_count':5,'off_target_scan':False,
       'species':'homo_sapiens','evitar_mode':'predesign','evitar_predict':'multifapredsi','ncores':1},
      ['design_sirna_with_evitar','compute_rna_sequence_gc_content','compute_sirna_duplex_binding_vienna','predict_rna_secondary_structure'],
      {'min_candidates':3,'gc_range':[0.3,0.7]}, 'PEDV fragment (1k nt)')

# 020 predesign + CRISPR
write('04_sirna_design_020_antiviral_predesign_crispr', 'full',
      'Antiviral Cas13 gRNA design with Evitar predesign mode and CRISPR predictor',
      {'mode':'antiviral','target_fasta_path':fasta,'candidate_count':5,'off_target_scan':False,
       'species':'homo_sapiens','evitar_mode':'predesign','evitar_predict':'CRISPR','ncores':1},
      ['design_sirna_with_evitar','compute_rna_sequence_gc_content','compute_sirna_duplex_binding_vienna','predict_rna_secondary_structure'],
      {'min_candidates':3,'gc_range':[0.3,0.7]}, 'PEDV fragment (1k nt)')

print('Extra tests written.')
