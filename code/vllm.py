# 完成了 R1_tool_call_Distill-Qwen-7B 模型的 vllm 部署
from vllm import LLM, SamplingParams
from transformers import AutoTokenizer
import os
import json

def get_completion(prompts, model, tokenizer=None, max_tokens=8192, temperature=0.6, top_p=0.95, max_model_len=2048):
    stop_token_ids = [151329, 151336, 151338]  # 根据运行效果可调整
    sampling_params = SamplingParams(
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stop_token_ids=stop_token_ids
    )
    llm = LLM(
        model=model,
        tokenizer=tokenizer,
        max_model_len=max_model_len,
        trust_remote_code=True
    )
    outputs = llm.generate(prompts, sampling_params)
    return outputs

# 测试部署情况的函数
if __name__ == "__main__":
    model = "hiieu/R1_tool_call_Distill-Qwen-7B"
    tokenizer = AutoTokenizer.from_pretrained(model, use_fast=False)

    text = [
        "请介绍计算机组成原理的课程结构和学习建议<think>\n",
    ]  # prompt 需以 <think>\n 结尾

    outputs = get_completion(
        text,
        model,
        tokenizer=tokenizer,
        max_tokens=8192,
        temperature=0.6,
        top_p=0.95,
        max_model_len=2048
    )

    for output in outputs:
        prompt = output.prompt
        generated_text = output.outputs[0].text
        if "</think>" in generated_text:
            think_content, answer_content = generated_text.split("</think>")
        else:
            think_content = ""
            answer_content = generated_text
        print(f"Prompt: {prompt!r}, Think: {think_content!r}, Answer: {answer_content!r}")

# 创建兼容 OpenAI API 接口的服务器命令行代码： python -m vllm.entrypoints.openai.api_server \
#   --served-model-name DeepSeek-R1 \
#   --max-model-len=2048
# 还需要在服务器上开放端口