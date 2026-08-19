"""Build a declarative form schema from a workflow's Pydantic input model."""

from __future__ import annotations

import inspect
from typing import (
    Any,
    Literal,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from typing_extensions import TypeAliasType


class FormField(BaseModel):
    """A single field in a workflow parameter form."""

    name: str
    type: Literal["str", "int", "float", "bool", "literal", "list", "dict", "file"]
    required: bool
    default: Any
    description: str
    ui_group: Literal["basic", "advanced"] = "basic"
    choices: list[str] | None = None
    item_type: Literal["str", "int", "float", "bool", "literal", "dict"] | None = None
    file_type_hint: str | None = None


class FormSchema(BaseModel):
    """Complete schema for a workflow's parameter form."""

    workflow: str
    workflow_title: str
    fields: list[FormField]


class FormSchemaBuilder:
    """Convert a Pydantic input model into a structured form schema."""

    # Prefixes that strongly indicate tool-level override parameters.
    _ADVANCED_PREFIXES: tuple[str, ...] = (
        "vienna_fold_",
        "linearfold_",
        "sirna_duplex_",
        "blastn_",
        "bowtie2_",
        "plfold_",
        "rnastop_",
        "rnaup_",
        "aso_accessibility_",
        "evitar_",
        "crgpt_",
        "crisot_",
        "rhodesign_",
        "ribodiffusion_",
        "rhofold_",
        "proteinx_",
        "egarps_",
        "extract_rna_",
        "interface_",
        "iresfinder_",
        "rnasmol_",
        "gernabind_",
        "inverse_fold_",
        "gc_",
        "u_content_",
        "unpaired_",
        "cai_",
    )

    # Substrings that indicate advanced / infrastructure parameters.
    _ADVANCED_SUBSTRINGS: tuple[str, ...] = (
        "service_url",
        "timeout_seconds",
        "device",
        "output_dir",
        "num_workers",
        "checkpoint_path",
        "ckpt_root_dir",
        "data_root_dir",
        "path_to_model",
        "model_path",
        "esm2_model_path",
        "cuda_visible_devices",
        "config_",
        "verbose",
        "fasta",  # format flags are usually advanced
    )

    # Names that are almost always core biological inputs.
    _BASIC_NAMES: frozenset[str] = frozenset(
        {
            "protein_sequence",
            "rna_sequence",
            "target_sequence",
            "sequence",
            "sequences",
            "target_structure",
            "secondary_structure",
            "structure_filepath",
            "secondary_structure_filepath",
            "sequence_filepath",
            "target_mrna_filepath",
            "smiles",
            "protein_structure_path",
            "protein_structure_filepath",
            "hotspots_protein_structure_path",
            "lineardesign_filepath",
            "rnarl_filepath",
            "gemorna_filepath",
            "crgpt_design_seed_sequence",
            "crgpt_design_filepath",
            "crisot_filepath",
            "crisot_target_sequence",
            "seed_sequence",
            "seed_filepath",
            "guide_sequence",
            "hotspot_residues",
            "aptamer_length",
            "n_odesign_samples",
            "odesign_seeds",
            "navigation",
            "n_samples",
            "n_samples_per_tool",
            "candidate_count",
            "repeats",
            "num_invocations",
            "aso_length",
            "window_step",
            "top_n_windows",
            "window_size",
            "step_size",
            "top_n_candidates",
            "probability_threshold",
            "reference_point",
            "target_cds_mfe",
            "target_cds_cai",
            "truncate_n_terminal",
            "truncate_c_terminal",
        }
    )

    # Core mode/tool-selection literals are basic even if their names don't match.
    _BASIC_LITERAL_FIELDS: frozenset[str] = frozenset(
        {
            "design_tool",
            "model_type",
            "utr_mode",
            "mode",
            "evitar_mode",
            "evitar_predict",
            "alignment_tool",
            "binding_evaluation_tool",
            "design_tools",
            "function_mode",
            "iresfinder_mode",
            "scoring_tools",
            "sampling_mode",
        }
    )

    @classmethod
    def from_pydantic_model(
        cls,
        workflow: str,
        model_cls: type[BaseModel],
        *,
        workflow_title: str = "",
    ) -> FormSchema:
        """Build a FormSchema from a workflow input model."""
        fields: list[FormField] = []
        for name, field_info in model_cls.model_fields.items():
            fields.append(cls._build_field(name, field_info))
        return FormSchema(
            workflow=workflow,
            workflow_title=workflow_title or workflow,
            fields=fields,
        )

    @classmethod
    def _build_field(cls, name: str, field_info: FieldInfo) -> FormField:
        annotation = field_info.annotation
        description = cls._get_description(field_info)
        default = cls._get_default(field_info)
        required = field_info.is_required()

        inner_type, is_optional = cls._unwrap_optional(annotation)
        type_name, choices, item_type = cls._resolve_type(inner_type)
        file_type_hint = cls._resolve_file_type_hint(name, description, type_name)

        if file_type_hint:
            type_name = "file"

        ui_group = cls._ui_group_for_field(name, field_info, inner_type, type_name)

        return FormField(
            name=name,
            type=type_name,
            required=required and not is_optional,
            default=default,
            description=description,
            ui_group=ui_group,
            choices=choices,
            item_type=item_type,
            file_type_hint=file_type_hint,
        )

    @staticmethod
    def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
        """Return (inner_type, is_optional)."""
        origin = get_origin(annotation)
        if origin is Union:
            args = [arg for arg in get_args(annotation) if arg is not type(None)]
            if len(args) == 1:
                return args[0], True
            if len(args) > 1:
                return Union[tuple(args)], True  # type: ignore[return-value]
        # Handle TypeAliasType (Pydantic 2.7+)
        if isinstance(annotation, TypeAliasType):
            return FormSchemaBuilder._unwrap_optional(annotation.__value__)
        return annotation, False

    @classmethod
    def _resolve_type(cls, annotation: Any) -> tuple[str, list[str] | None, str | None]:
        """Return (type_name, choices_for_literal, item_type_for_list)."""
        origin = get_origin(annotation)

        if origin is list or annotation is list:
            args = get_args(annotation)
            item_type_name, _, _ = cls._resolve_type(args[0]) if args else ("str", None, None)
            return "list", None, item_type_name

        if origin is Literal or str(annotation).startswith("typing.Literal"):
            choices = [str(arg) for arg in get_args(annotation)]
            return "literal", choices, None

        if annotation is int:
            return "int", None, None
        if annotation is float:
            return "float", None, None
        if annotation is bool:
            return "bool", None, None
        if annotation is str:
            return "str", None, None
        if annotation is dict or origin is dict:
            return "dict", None, None

        # Fall back to str for unrecognized types so the form remains usable.
        return "str", None, None

    @staticmethod
    def _get_default(field_info: FieldInfo) -> Any:
        if field_info.is_required():
            return None
        default = field_info.default
        if default is inspect.Parameter.empty or default is None:
            return None
        return default

    @staticmethod
    def _get_description(field_info: FieldInfo) -> str:
        desc = field_info.description or ""
        if field_info.json_schema_extra and isinstance(field_info.json_schema_extra, dict):
            desc = field_info.json_schema_extra.get("description", desc) or desc
        return desc

    @classmethod
    def _resolve_file_type_hint(cls, name: str, description: str, type_name: str) -> str | None:
        """Return a hint like 'fasta', 'pdb', 'json' if this field is clearly a file path."""
        lowered = f"{name} {description}".lower()

        if type_name != "str" and type_name != "file":
            return None
        if "filepath" in name or "_path" in name or "_file" in name:
            if any(ext in lowered for ext in [".fasta", "fasta", "sequence file"]):
                return "fasta"
            if any(ext in lowered for ext in [".pdb", ".cif", "structure file", "pdb/cif"]):
                return "structure"
            if any(ext in lowered for ext in [".npy", "contact map", "contact-map"]):
                return "npy"
            if any(ext in lowered for ext in [".json", "json"]):
                return "json"
            if any(ext in lowered for ext in [".csv", "csv"]):
                return "csv"
            if any(ext in lowered for ext in [".txt", "plain text"]):
                return "text"
            return "file"
        return None

    @classmethod
    def _ui_group_for_field(
        cls,
        name: str,
        field_info: FieldInfo,
        inner_type: Any,
        type_name: str,
    ) -> Literal["basic", "advanced"]:
        # 1. Explicit schema metadata wins.
        extra = field_info.json_schema_extra
        if isinstance(extra, dict):
            ui_group = extra.get("ui_group")
            if ui_group in ("basic", "advanced"):
                return ui_group  # type: ignore[return-value]

        # 2. Known core biological inputs are basic.
        if name in cls._BASIC_NAMES:
            return "basic"

        # 3. Known core mode/tool literals are basic.
        if name in cls._BASIC_LITERAL_FIELDS:
            return "basic"

        # 4. Advanced substrings / prefixes.
        if any(name.startswith(prefix) for prefix in cls._ADVANCED_PREFIXES):
            return "advanced"
        if any(sub in name for sub in cls._ADVANCED_SUBSTRINGS):
            return "advanced"

        # 5. Anything else is basic by default.
        return "basic"
