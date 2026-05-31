import torch
import torchvision.models as models
import argparse
import os

MODEL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def export_mobilenetv3_onnx(output_path: str = "models/reid_mobilenet_v3.onnx"):
    model = models.mobilenet_v3_small(
        weights=models.MobileNet_V3_Small_Weights.DEFAULT
    )
    model.classifier[-1] = torch.nn.Identity()
    model = model.cpu()
    model.eval()

    dummy = torch.randn(1, 3, 256, 128)

    torch.onnx.export(
        model,
        dummy,
        output_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}},
    )

    print(f"ONNX model exported to {output_path}")

    import onnxruntime as ort

    session = ort.InferenceSession(output_path)
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    result = session.run([output_name], {input_name: dummy.numpy()})
    print(f"Output shape: {result[0].shape}")
    print(f"Feature dimension: {result[0].shape[1]}")
    print("ONNX verification OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default=os.path.join(MODEL_DIR, "models", "reid_mobilenet_v3.onnx"),
    )
    args = parser.parse_args()
    export_mobilenetv3_onnx(args.output)
