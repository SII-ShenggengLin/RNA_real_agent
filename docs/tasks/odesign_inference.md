# 任务：`odesign_inference`

## 任务目标

对显式 JSON 定义的设计任务运行 ODesign 推理并输出预测文件集合。

## 输入 / 输出

- **输入**：`input_json_filepath`
- **输出**：`output_dir`、`prediction_filepaths`、日志文件

## 前置条件

- ODesign 微服务（端口 8012），通常依赖 GPU/权重/数据文件

## 工具

- `run_odesign_inference`

## 标准工具链

见 `docs/workflows/odesign_inference_workflow.md`。

