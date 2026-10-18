# mod_ai — AI 引擎模块

## 职责

提供 AI 推理能力，包括图像分类、人脸检测、相似性去重。

## 对外接口

```python
from modules.mod_ai import (
    AIEngine,           # 抽象基类
    CPUEngine,          # ONNX Runtime CPU 推理
    BM1688Engine,       # 算能 NPU 推理
    FaceEngine,         # 人脸检测
    get_ai_engine,      # 获取引擎实例
    get_engine_status,  # 获取引擎状态
)
```

## AIEngine 抽象方法

| 方法 | 说明 |
|------|------|
| `image_predict(filepath)` | 图像分类 → `{tags, feature, confidence}` |
| `video_predict(filepath)` | 视频分析 → `{tags, audio_tags, duration, feature}` |
| `face_detect(filepath)` | 人脸检测 → `{faces, embeddings}` |
| `deduplicate(feature, threshold)` | 相似性去重 → `[相似文件路径]` |

## 获取引擎实例

```python
from modules.mod_ai import get_ai_engine

# 自动选择可用引擎
engine = get_ai_engine('cpu')      # ONNX CPU
engine = get_ai_engine('bm1688')   # 算能 NPU
engine = get_ai_engine('face')     # 人脸检测
```

## CPUEngine 配置

```yaml
ai:
  engine: cpu
  model_path: models/mobilenetv2-7.onnx
  input_size: [224, 224]
  threshold: 0.3
  batch_size: 8
```

引擎自动回退策略：
1. 本地 ONNX 模型
2. 自动下载 MobileNetV2 (~14MB)
3. 启发式颜色分类（heuristic）

## 依赖

- `core.logger`
- `numpy`, `PIL`, `onnxruntime` (CPU)
- `sophon` (BM1688，可选)
