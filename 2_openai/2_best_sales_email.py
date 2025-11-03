from dotenv import load_dotenv
from agents import Agent, Runner, trace, function_tool
from openai.types.responses import ResponseTextDeltaEvent
from typing import Dict
import requests
import os
import asyncio

load_dotenv(override=True)
RESEND_API_KEY = os.getenv('RESEND_API_KEY')

instructions1 = "You are a sales agent working for ComplAI, \
a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. \
You write professional, serious cold emails."

instructions2 = "You are a humorous, engaging sales agent working for ComplAI, \
a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. \
You write witty, engaging cold emails that are likely to get a response."

instructions3 = "You are a busy sales agent working for ComplAI, \
a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI. \
You write concise, to the point cold emails."

sales_agent_1 = Agent(
    name="Professional Sales Agent",
    instructions=instructions1,
    model="gpt-4o-mini"
)

sales_agent_2 = Agent(
    name="Engaging Sales Agent",
    instructions=instructions2,
    model="gpt-4o-mini"
)

sales_agent_3 = Agent(
    name="Busy Sales Agent",
    instructions=instructions3,
    model="gpt-4o-mini"
)

result = Runner.run_streamed(sales_agent_1, input="Write a cold sales email")
async for event in result.stream_events():
    if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
        print(event.data.delta, end="", flush=True)

message = "Write a cold sales email"

with trace("Parallel col emails"):
    results = await asyncio.gather(
        Runner.run(sales_agent_1, message),
        Runner.run(sales_agent_2, message),
        Runner.run(sales_agent_3, message),
    )

outputs = [result.final_output for result in results]
for output in outputs:
    print(output + "\n\n")

sales_picker = Agent(
    name="sales_picker",
    instructions="You pick the best cold sales email from the given options. \
Imagine you are a customer and pick the one you are most likely to respond to. \
Do not give an explanation; reply with the selected email only.",
    model="gpt-4o-mini"
)


message = "Write a cold sales email"

with trace("Selection from sales people"):
    results = await asyncio.gather(
        Runner.run(sales_agent_1, message),
        Runner.run(sales_agent_2, message),
        Runner.run(sales_agent_3, message)
    )
    output = [result.final_output for result in results]

    emails = "Cold sales emails: \n\n".join(outputs)

    best = await Runner.run(sales_picker, emails)

    print(f"Best sales email:\n{best.final_output}")


@function_tool
def send_email(body: str):
    """Send out an email with the given body to all sales prospects via Resend."""

    from_email = "opolskaya.alina@yandex.ru"
    to_email = "opolskaia.alina@gmail.com"

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "from": f"Alina <{from_email}>",
        "to": [to_email],
        "subject": "Sales email",
        "html": f"<p>{body}</p>"
    }

    response = requests.post("https://api.resend.com/emails", json=payload, headers=headers)

    if response.status_code == 202:
        return {"status": "success"}
    else:
        return {"status": "failure", "message": response.text}
    

# converting Agents to tools
description = "Write a cold sales email"

tool_1 = sales_agent_1.as_tool(tool_name="sales_agent_1", tool_description=description)
tool_2 = sales_agent_2.as_tool(tool_name="sales_agent_2", tool_description=description)
tool_3 = sales_agent_3.as_tool(tool_name="sales_agent_3", tool_description=description)

tools = [tool_1, tool_2, tool_3, send_email]



