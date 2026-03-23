from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
import asyncio

# sk-9b57b709bc8843b798537cc32546169e

# from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek

import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    model = ChatDeepSeek(model="deepseek-chat")

    async with MultiServerMCPClient(
        {
            "mind_map": {
                "command": "python",
                # Make sure to update to the full absolute path to your math_server.py file
                "args": ["/home/rrpan/ai/mindmap-mcp-server/mindmap_mcp_server/server.py"],
                "transport": "stdio",
            },
            "take_note":{
                "command": "python",
                # Make sure to update to the full absolute path to your math_server.py file
                "args": ["/home/rrpan/ai/MCP-Doc/server.py"],
                "transport": "stdio",
            },
            "weather": {
                # make sure you start your weather server on port 8000
                "url": "http://localhost:8000/sse",
                "transport": "sse",
            },
            "baidu-search": {
                "url": os.environ["BD_URL"],
                "transport": "sse",
            }
            
        }
    ) as client:
        agent = create_react_agent(model, client.get_tools())
        note_response = await agent.ainvoke({"messages": "数据库里有哪些关键概念？生成笔记"})
        html_response = await agent.ainvoke({"messages": "数据库里有哪些关键概念？生成思维导图"})
        # weather_response = await agent.ainvoke({"messages": "what is the weather in nyc?"})
        # search_response = await agent.ainvoke({"messages": "搜索什么是百度"})
        # print("Math result:", math_response)
        
        import datetime
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with open(f"note_{timestamp}.txt", "w", encoding="utf-8") as f:
            f.write(note_response['messages'][0].content if isinstance(note_response, dict) else str(note_response))

        # 保存 HTML 文件
        with open(f"mindmap_{timestamp}.html", "w", encoding="utf-8") as f:
            for msg in html_response.get("messages", []):
                if hasattr(msg, "content"):
                    f.write(msg.content)
                
        print("note result:", note_response)
        # print("Weather result:", weather_response)
        print("html result:", html_response)

        
asyncio.run(main())