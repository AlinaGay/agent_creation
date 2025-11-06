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

instructions ="You are a sales manager working for ComplAI. You use the tools given to you to generate cold sales emails. \
You never generate sales emails yourself; you always use the tools. \
You try all 3 sales_agent tools once before choosing the best one. \
You pick the single best email and use the send_email tool to send the best email (and only the best email) to the user."

sales_manager = Agent(name="Sales Manager", instructions=instructions, tools=tools, model="gpt-4o-mini")

message = "Send a cold sales email addressed to 'Dear CEO'"

with trace("Sales manager"):
    result = await Runner.run(sales_manager, message)


subject_instructions = "You can write a subject for a cold sales email. \
You are given a message and you need to write a subject for an email that is likely to get a response."

html_instructions = "You can convert a text email body to an HTML email body. \
You are given a text email body which might have some markdown \
and you need to convert it to an HTML email body with simple, clear, compelling layout and design."

subject_writer = Agent(name="Email subject writer", instructions=subject_instructions, model="gpt-4o-mini")
subject_tool = subject_writer.as_tool(tool_name="subject_writer", tool_description="Write a subject for a cold sales email")

html_converter = Agent(name="HTML email body converter", instructions=html_instructions, model="gpt-4o-mini")
html_tool = html_converter.as_tool(tool_name="html_converter", tool_description="Convert a text email body to an HTML email body")

@function_tool
def send_html_email(subject: str, html_body: str) -> Dict[str, str]:
    """Send out an email with the given subject and HTML body to all sales prospects using Resend"""

    from_email = "opolskaya.alina@yandex.ru"
    to_email = "opolskaia.alina@gmail.com"

    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "from": f"Alina <{from_email}>",
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }

    response = requests.post("https://api.resend.com/emails", json=payload, headers=headers)

    if response.status_code == 202:
        return {"status": "success"}
    else:
        return {"status": "failure", "message": response.text}
    
instructions ="You are an email formatter and sender. You receive the body of an email to be sent. \
You first use the subject_writer tool to write a subject for the email, then use the html_converter tool to convert the body to HTML. \
Finally, you use the send_html_email tool to send the email with the subject and HTML body."

emailer_agent = Agent(
    name="Email Manager",
    instructions=instructions,
    tools=tools,
    model="gpt-4o-mini",
    handoff_description="Convert an email to HTML and send it"
)

tools = [tool_1, tool_2, tool_3]
handoffs = [emailer_agent]

sales_manager_instructions = "You are a sales manager working for ComplAI. You use the tools given to you to generate cold sales emails. \
You never generate sales emails yourself; you always use the tools. \
You try all 3 sales agent tools at least once before choosing the best one. \
You can use the tools multiple times if you're not satisfied with the results from the first try. \
You select the single best email using your own judgement of which email will be most effective. \
After picking the email, you handoff to the Email Manager agent to format and send the email."

sales_manager = Agent(
    name="Sales Manager",
    instructions=sales_manager_instructions,
    tools=tools,
    handoffs=handoffs,
    model="gpt-4o-mini"
)

message = "Send out a cold sales email addressed to Dear CEO from Alice"

with trace("Automated SDR"):
    result = await Runner.run(sales_manager, message)
