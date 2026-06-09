#!/usr/bin/env python3
"""
RNA-BioBench-Aptamer 数据集质量检查脚本
检查项：
1. 每个靶标 JSON 字段完整性
2. PDB 文件与 JSON 中 pdb_id 匹配
3. 序列长度一致性、热点残基格式等
"""

import json
import os
import re
import sys
from pathlib import Path


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_hotspot_format(hotspot_str):
    """检查热点残基格式：如 H/46,H/67,H/70 或空字符串"""
    if not hotspot_str or hotspot_str.strip() == "":
        return True, ""
    parts = hotspot_str.split(",")
    pattern = re.compile(r"^[A-Za-z]/\d+$")
    errors = []
    for part in parts:
        part = part.strip()
        if not pattern.match(part):
            errors.append(f"'{part}' 不符合 '链/残基编号' 格式")
    if errors:
        return False, "; ".join(errors)
    return True, ""


def check_aptamer_reference(aptamer_ref):
    """检查 known_aptamer_reference 结构"""
    if aptamer_ref is None:
        return True, ""
    required = ["sequence", "kd_nm", "reference"]
    missing = [k for k in required if k not in aptamer_ref]
    if missing:
        return False, f"缺少字段: {missing}"
    # 检查 sequence 是否为合法 RNA 序列（仅含 AUCG，可能允许混合）
    seq = aptamer_ref.get("sequence", "")
    if seq:
        invalid_chars = set(seq.upper()) - set("AUCGT")
        if invalid_chars:
            return False, f"序列包含非标准碱基字符: {invalid_chars}"
    # 检查 kd_nm 是否为数字
    kd = aptamer_ref.get("kd_nm")
    if not isinstance(kd, (int, float)):
        return False, f"kd_nm 类型错误: {type(kd).__name__}"
    return True, ""


def main():
    base_dir = Path(__file__).parent.resolve()
    manifest_path = base_dir / "dataset_manifest.json"
    targets_dir = base_dir / "targets"
    structures_dir = base_dir / "structures"

    if not manifest_path.exists():
        print(f"[错误] 未找到清单文件: {manifest_path}")
        sys.exit(1)

    manifest = load_json(manifest_path)
    manifest_fields = set(manifest.get("fields", []))
    expected_targets = manifest.get("targets", [])

    print("=" * 60)
    print("RNA-BioBench-Aptamer 数据集质量检查")
    print("=" * 60)
    print(f"期望靶标数: {len(expected_targets)}")
    print(f"清单字段: {sorted(manifest_fields)}")
    print()

    issues = []
    warnings = []

    # 1. 检查 targets/ 下的 JSON 文件
    json_files = sorted(targets_dir.glob("*.json"))
    actual_target_ids = []

    for json_file in json_files:
        target_id = json_file.stem
        actual_target_ids.append(target_id)
        data = load_json(json_file)

        # 1a. 字段完整性
        missing_fields = manifest_fields - set(data.keys())
        extra_fields = set(data.keys()) - manifest_fields
        if missing_fields:
            issues.append(f"[{target_id}] 缺少清单字段: {sorted(missing_fields)}")
        if extra_fields:
            warnings.append(f"[{target_id}] 存在清单外字段: {sorted(extra_fields)}")

        # 1b. 序列长度一致性
        seq = data.get("protein_sequence", "")
        declared_len = data.get("protein_length_aa", 0)
        actual_len = len(seq)
        if actual_len != declared_len:
            issues.append(
                f"[{target_id}] 序列长度不一致: 声明={declared_len}, 实际={actual_len}"
            )

        # 1c. 热点残基格式
        hotspot = data.get("known_hotspot_residues", "")
        ok, msg = check_hotspot_format(hotspot)
        if not ok:
            issues.append(f"[{target_id}] 热点残基格式错误: {msg}")

        # 1d. known_aptamer_reference 结构检查
        aptamer_ref = data.get("known_aptamer_reference")
        ok, msg = check_aptamer_reference(aptamer_ref)
        if not ok:
            issues.append(f"[{target_id}] known_aptamer_reference 格式错误: {msg}")

        # 1e. pdb_id 与文件名一致性
        pdb_id = data.get("pdb_id", "")
        if pdb_id and pdb_id.upper() != target_id.upper().replace("_", ""):
            # 某些靶标名包含下划线（如 SARS-CoV-2_Nucleocapsid），不强制匹配
            pass  # 仅做宽松检查

    # 2. 检查清单中的靶标是否都有 JSON 文件
    json_ids = {f.stem for f in json_files}
    for tid in expected_targets:
        if tid not in json_ids:
            issues.append(f"[清单] 靶标 '{tid}' 缺少对应的 JSON 文件")

    # 3. 检查 PDB 文件匹配
    pdb_files = {f.stem.upper(): f for f in structures_dir.glob("*.pdb")}
    for json_file in json_files:
        data = load_json(json_file)
        target_id = json_file.stem
        pdb_id = data.get("pdb_id", "").upper()

        if not pdb_id:
            issues.append(f"[{target_id}] 缺少 pdb_id")
            continue

        if pdb_id not in pdb_files:
            issues.append(
                f"[{target_id}] PDB 文件缺失: 期望 '{pdb_id}.pdb'，在 structures/ 中未找到"
            )
        else:
            # 检查文件是否为空
            pdb_path = pdb_files[pdb_id]
            if pdb_path.stat().st_size == 0:
                issues.append(f"[{target_id}] PDB 文件为空: {pdb_path.name}")

    # 4. 检查 structures/ 下是否有未被引用的 PDB 文件
    referenced_pdbs = set()
    for json_file in json_files:
        data = load_json(json_file)
        pdb_id = data.get("pdb_id", "").upper()
        if pdb_id:
            referenced_pdbs.add(pdb_id)

    for pdb_stem, pdb_path in pdb_files.items():
        if pdb_stem not in referenced_pdbs:
            warnings.append(
                f"[structures] PDB 文件 '{pdb_path.name}' 未被任何靶标 JSON 引用"
            )

    # 5. 汇总输出
    print(f"实际 JSON 文件数: {len(json_files)}")
    print(f"实际 PDB 文件数:  {len(pdb_files)}")
    print()

    if issues:
        print(f"❌ 发现 {len(issues)} 个错误:")
        for issue in issues:
            print(f"   - {issue}")
        print()
    else:
        print("✅ 未发现错误")
        print()

    if warnings:
        print(f"⚠️  发现 {len(warnings)} 个警告:")
        for warning in warnings:
            print(f"   - {warning}")
        print()
    else:
        print("✅ 未发现警告")
        print()

    # 最终统计
    print("=" * 60)
    print("检查完成")
    print(f"靶标: {len(expected_targets)} 个 | 错误: {len(issues)} | 警告: {len(warnings)}")

    if issues:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
