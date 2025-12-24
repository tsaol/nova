// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.core.SdkBytes;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelRequest;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelResponse;
import software.amazon.awssdk.services.bedrockruntime.model.ServiceTierType;
import org.json.JSONArray;
import org.json.JSONObject;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Base64;

/**
 * Flex Tier 图片推理使用示例
 * 使用方法：在调用 invokeModel 时添加 serviceTier("flex") 参数
 */
public class FlexTierDemo {

    public static void main(String[] args) {
        // 创建 Bedrock Runtime 客户端
        BedrockRuntimeClient client = BedrockRuntimeClient.builder()
                .region(Region.US_WEST_2)
                .credentialsProvider(DefaultCredentialsProvider.create())
                .build();

        try {
            System.out.println("============================================================");
            System.out.println("使用 Flex Tier 进行图片推理");
            System.out.println("============================================================");

            // 读取图片并转换为 Base64
            String imagePath = "../images/test1.png";
            byte[] imageBytes = Files.readAllBytes(Paths.get(imagePath));
            String base64Image = Base64.getEncoder().encodeToString(imageBytes);
            
            System.out.println("图片: " + imagePath + "\n");

            // 构建请求体
            JSONObject requestBody = new JSONObject();
            requestBody.put("schemaVersion", "messages-v1");

            // 构建消息内容
            JSONArray messages = new JSONArray();
            JSONObject message = new JSONObject();
            message.put("role", "user");

            JSONArray content = new JSONArray();
            
            // 添加图片
            JSONObject imageContent = new JSONObject();
            JSONObject image = new JSONObject();
            JSONObject source = new JSONObject();
            source.put("bytes", base64Image);
            image.put("format", "png");
            image.put("source", source);
            imageContent.put("image", image);
            content.put(imageContent);

            // 添加文本提示
            JSONObject textContent = new JSONObject();
            textContent.put("text", "Describe this image in detail.");
            content.put(textContent);

            message.put("content", content);
            messages.put(message);
            requestBody.put("messages", messages);

            // 添加推理配置
            JSONObject inferenceConfig = new JSONObject();
            inferenceConfig.put("maxTokens", 512);
            inferenceConfig.put("temperature", 0.7);
            requestBody.put("inferenceConfig", inferenceConfig);

            // 构建 InvokeModel 请求，添加 serviceTier
            InvokeModelRequest request = InvokeModelRequest.builder()
                    .modelId("global.amazon.nova-2-lite-v1:0")
                    .contentType("application/json")
                    .accept("application/json")
                    .body(SdkBytes.fromUtf8String(requestBody.toString()))
                    .serviceTier(ServiceTierType.FLEX)  // 关键参数：指定使用 flex tier
                    .build();

            // 调用模型
            InvokeModelResponse response = client.invokeModel(request);

            // 打印完整返回报文
            System.out.println("============================================================");
            System.out.println("完整返回报文");
            System.out.println("============================================================");

            // 打印响应元数据
            System.out.println("\n【Response Metadata】");
            System.out.println("Request ID: " + response.responseMetadata().requestId());
            System.out.println("HTTP Status Code: " + response.sdkHttpResponse().statusCode());
            
            System.out.println("\n【HTTP Headers】");
            response.sdkHttpResponse().headers().forEach((key, values) -> {
                values.forEach(value -> System.out.println(key + ": " + value));
            });

            // 解析响应体
            String responseBody = response.body().asUtf8String();
            JSONObject result = new JSONObject(responseBody);
            
            System.out.println("\n【Response Body】");
            System.out.println(result.toString(2));

            // 提取关键信息
            System.out.println("\n============================================================");
            System.out.println("关键信息提取");
            System.out.println("============================================================");

            String responseText = result.getJSONObject("output")
                    .getJSONObject("message")
                    .getJSONArray("content")
                    .getJSONObject(0)
                    .getString("text");

            System.out.println("\n响应内容:");
            System.out.println(responseText);

            // 验证实际使用的 Service Tier
            String actualTier = response.sdkHttpResponse()
                    .firstMatchingHeader("x-amzn-bedrock-service-tier")
                    .orElse("unknown");

            System.out.println("\n验证实际使用的 Service Tier:");
            System.out.println("  请求的 Tier: flex");
            System.out.println("  实际使用的 Tier: " + actualTier);

            if ("flex".equals(actualTier)) {
                System.out.println("  ✅ 确认：成功使用 Flex Tier");
            } else {
                System.out.println("  ⚠️  注意：实际使用的是 " + actualTier + " tier，而不是 flex tier");
            }

            // 使用说明
            System.out.println("\n============================================================");
            System.out.println("Flex Tier 图片推理使用说明");
            System.out.println("============================================================");
            System.out.println("""
                    
📝 使用方法：
// 1. 读取并编码图片
byte[] imageBytes = Files.readAllBytes(Paths.get("image.png"));
String base64Image = Base64.getEncoder().encodeToString(imageBytes);

// 2. 构建包含图片的请求体（JSON）
JSONObject requestBody = new JSONObject();
// ... 构建消息内容 ...

// 3. 调用时添加 serviceTier
InvokeModelRequest request = InvokeModelRequest.builder()
    .modelId("us.amazon.nova-2-lite-v1:0")
    .body(SdkBytes.fromUtf8String(requestBody.toString()))
    .serviceTier(ServiceTierType.FLEX)  // 添加此参数
    .build();

InvokeModelResponse response = client.invokeModel(request);

🔍 如何验证实际使用的 Tier：
从响应头中读取 x-amzn-bedrock-service-tier：

String actualTier = response.sdkHttpResponse()
    .firstMatchingHeader("x-amzn-bedrock-service-tier")
    .orElse("unknown");
System.out.println("实际使用的 Tier: " + actualTier);

如果返回 "flex"，说明成功使用了 Flex Tier
                    """);

        } catch (IOException e) {
            System.err.println("读取图片文件失败: " + e.getMessage());
            e.printStackTrace();
        } catch (Exception e) {
            System.err.println("调用 Bedrock 失败: " + e.getMessage());
            e.printStackTrace();
        } finally {
            client.close();
        }
    }
}
