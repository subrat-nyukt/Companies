import json
import os
import re 
import logging
from typing import Dict, List, Any, Awaitable

from agent_prompt import SYSTEM_PROMPT


logger=logging.get_logger()


Tools =[
    {

        "type": "function",
        "function":{
            "name":"check_specialty_availability",
            "desctiption":"Check availability of doctors for a specific specialty",
            "parameters":{
                "type":"object",
                "preporties":{
                    "specialty":{
                        "type":"string",
                        "description":"Specialty of the doctor"
                    }
                },
                "required":["specialty"]
            }
            
        }

    }
]



opening_Greetings = ("नमस्ते, कीम्स मेडिकल  में आपका स्वागत है। "
    "मैं आपकी अपॉइंटमेंट बुक करने में सहायता कर सकती हूँ। "
    "आप ओड़िया, हिंदी या English में बात कर सकते हैं।")



class conversation:

    def __init__(self,call_sid,from_number,call_executor,on_thinking):

        self.call_sid=call_sid
        self.from_number=from_number
        self.call_executor=call_executor
        self.on_thinking=on_thinking

        self.messages=[]

        self.messages.append("role":"system","content":SYSTEM_PROMPT.replace({{"from_number"}},from_number))

        self.messages.append("role":"assistant",content:opening_Greetings)



        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=self.messages,
            tools=Tools,
            temperature=0.2
            
        )

        result=response.choices[0].message


async def get_response(user_query:str, lan:str="en"):

    tagged= f'language is {lang} {user_query}'

    self.messages.append("role":"user", "content":tagged)


    if self.on_thinking:
        await .self.onthinking(lang)


        response = self.client.chat.completion.create(
            model="gpt-4o",
            messages=self.messages,
            tools=Tools,
            temperature=0.2
            
        )

        result=response.choices[0].message


        if not ms.tool_calls:
            text= result.content

            self.messages("role":"assistant","content":text)
    

            return text


            self.messages.append(result)

        
        for tc in msg.tool_calls:

            name=tc.function.name

            args=json.loads(tc.function.arguments)


            result = await self.tool_executor(name,args,self.call_sid,self.from_number)

            self.messages.append({"role":"tool","tool_call_id":tc.id,"content":result})





        
            













