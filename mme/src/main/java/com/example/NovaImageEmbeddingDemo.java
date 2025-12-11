package com.example;

import org.json.JSONArray;
import org.json.JSONObject;
import software.amazon.awssdk.core.SdkBytes;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelRequest;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelResponse;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Base64;

/**
 * Amazon Nova Multimodal Embeddings (MME) - 图片嵌入 API 演示
 * 展示如何使用 Nova MME API 获取图片的嵌入向量
 */
public class NovaImageEmbeddingDemo {

    private static final String MODEL_ID = "amazon.nova-2-multimodal-embeddings-v1:0";
    private static final Region REGION = Region.US_EAST_1;

    public static void main(String[] args) {
        try {
            // 1. 创建 Bedrock Runtime 客户端
            BedrockRuntimeClient client = BedrockRuntimeClient.builder()
                    .region(REGION)
                    .build();

            // 2. 加载图片并转换为 base64
            String imagePath = "../images/test1.png";
            System.out.println("正在加载图片: " + imagePath);

            byte[] imageBytes = Files.readAllBytes(Paths.get(imagePath));
            String imageBase64 = Base64.getEncoder().encodeToString(imageBytes);

            // 3. 构建请求体 - 图片嵌入
            JSONObject requestBody = new JSONObject();
            requestBody.put("taskType", "SINGLE_EMBEDDING");

            JSONObject singleEmbeddingParams = new JSONObject();
            singleEmbeddingParams.put("embeddingPurpose", "GENERIC_INDEX");
            singleEmbeddingParams.put("embeddingDimension", 1024);

            JSONObject image = new JSONObject();
            image.put("format", "png");

            JSONObject source = new JSONObject();
            source.put("bytes", imageBase64);
            image.put("source", source);

            singleEmbeddingParams.put("image", image);
            requestBody.put("singleEmbeddingParams", singleEmbeddingParams);

            // 4. 调用 Nova MME 模型
            System.out.println("正在调用 Nova Multimodal Embeddings 模型...");

            InvokeModelRequest request = InvokeModelRequest.builder()
                    .modelId(MODEL_ID)
                    .contentType("application/json")
                    .accept("application/json")
                    .body(SdkBytes.fromUtf8String(requestBody.toString()))
                    .build();

            InvokeModelResponse response = client.invokeModel(request);

            // 5. 解析响应
            String responseBody = response.body().asUtf8String();
            JSONObject jsonResponse = new JSONObject(responseBody);
            JSONArray embeddings = jsonResponse.getJSONArray("embeddings");
            JSONObject embeddingObj = embeddings.getJSONObject(0);
            JSONArray embedding = embeddingObj.getJSONArray("embedding");
            String embeddingType = embeddingObj.getString("embeddingType");

            // 6. 输出结果
            System.out.println("\n✅ 成功生成图片嵌入向量！");
            System.out.println("   向量维度: " + embedding.length());
            System.out.println("   嵌入类型: " + embeddingType);

            // 输出前 10 个值
            System.out.print("   前 10 个值: [");
            for (int i = 0; i < Math.min(10, embedding.length()); i++) {
                System.out.print(embedding.getDouble(i));
                if (i < 9) System.out.print(", ");
            }
            System.out.println("]");

            client.close();

        } catch (IOException e) {
            System.err.println("\n❌ 错误: " + e.getMessage());
            System.err.println("\n💡 提示:");
            System.err.println("  ⚠️  图片文件路径问题");
            System.err.println("  1. 确保图片文件存在: images/test1.png");
            System.err.println("  2. 或修改 imagePath 变量为正确的路径");
        } catch (Exception e) {
            System.err.println("\n❌ 错误: " + e.getMessage());
            System.err.println("\n💡 提示:");

            String errorMsg = e.getMessage();
            if (errorMsg != null && (errorMsg.contains("ValidationException") || errorMsg.contains("invalid"))) {
                System.err.println("  ⚠️  模型未启用或不可用");
                System.err.println("  1. 访问 Bedrock 控制台: https://console.aws.amazon.com/bedrock/");
                System.err.println("  2. 在左侧菜单选择 'Model access'");
                System.err.println("  3. 点击 'Manage model access'");
                System.err.println("  4. 找到 'Amazon Nova Multimodal Embeddings' 并启用");
            } else if (errorMsg != null && (errorMsg.contains("credentials") || errorMsg.contains("auth"))) {
                System.err.println("  ⚠️  AWS 凭证问题");
                System.err.println("  1. 配置 AWS 凭证");
                System.err.println("  2. 确保有正确的 IAM 权限");
            } else {
                System.err.println("  1. 确保已在 Bedrock 控制台启用 Nova Multimodal Embeddings 模型");
                System.err.println("  2. 确保 AWS 凭证配置正确");
                System.err.println("  3. 确保使用 us-east-1 区域");
            }
        }
    }
}
