import json

# Update bolna_tool_schemas.py
with open("bolna_tool_schemas.py", "r", encoding="utf-8") as f:
    schema_content = f.read()

old_enum = '''"enum": [
                            "Suresh Mahapatra", "Priya Nanda", "Ramesh Pattnaik", 
                            "Anjali Mishra", "Bikash Mohanty", "Sarita Das", 
                            "Arun Sahoo", "Lipsa Rath", "Nirmal Behera"
                        ],'''

new_enum = '''"enum": [
                            "ANUPAM JENA", "SUBASIS MISHRA", "SANTOSH RATH", 
                            "DEBASHIS MISHRA", "OM MISHRA", "PRERANA DASH"
                        ],'''

schema_content = schema_content.replace(old_enum, new_enum)

old_doc_desc = '''DR001=Dr. Suresh Mahapatra, DR002=Dr. Priya Nanda, DR003=Dr. Ramesh Pattnaik, DR004=Dr. Anjali Mishra, DR005=Dr. Bikash Mohanty, DR006=Dr. Sarita Das, DR007=Dr. Arun Sahoo, DR008=Dr. Lipsa Rath, DR009=Dr. Nirmal Behera'''
new_doc_desc = '''DR001=Dr. ANUPAM JENA, DR002=Dr. SUBASIS MISHRA, DR003=Dr. SANTOSH RATH, DR004=Dr. DEBASHIS MISHRA, DR005=Dr. OM MISHRA, DR006=Dr. PRERANA DASH'''

schema_content = schema_content.replace(old_doc_desc, new_doc_desc)

with open("bolna_tool_schemas.py", "w", encoding="utf-8") as f:
    f.write(schema_content)

# Update agent_prompt.py
with open("agent_prompt.py", "r", encoding="utf-8") as f:
    prompt_content = f.read()

old_step_2 = '''STEP 2 — List Doctors in that Department
  - Once they say the department (e.g. Cardiology), list the available doctors in that department.
  - Odia: "ଏହି ବିଭାଗରେ ଉପଲବ୍ଧ ଡାକ୍ତରମାନେ ହେଉଛନ୍ତି [Doctor names]."'''

new_step_2 = '''STEP 2 — List Doctors in that Department
  - Once they say the department (e.g. Cardiology), you MUST first say "ଟିକେ ମୁହୂର୍ତ୍ତ ଅପେକ୍ଷା କରନ୍ତୁ" to acknowledge them and then list the available doctors.
  - Odia: "ଟିକେ ମୁହୂର୍ତ୍ତ ଅପେକ୍ଷା କରନ୍ତୁ। ଏହି ବିଭାଗରେ ଉପଲବ୍ଧ ଡାକ୍ତରମାନେ ହେଉଛନ୍ତି [Doctor names]."'''

prompt_content = prompt_content.replace(old_step_2, new_step_2)

old_list_doc_str = '''- List Doctors in Department: "ଏହି ବିଭାଗରେ ଉପଲବ୍ଧ ଡାକ୍ତରମାନେ ହେଉଛନ୍ତି [Doctor names]."'''
new_list_doc_str = '''- List Doctors in Department: "ଟିକେ ମୁହୂର୍ତ୍ତ ଅପେକ୍ଷା କରନ୍ତୁ। ଏହି ବିଭାଗରେ ଉପଲବ୍ଧ ଡାକ୍ତରମାନେ ହେଉଛନ୍ତି [Doctor names]."'''

prompt_content = prompt_content.replace(old_list_doc_str, new_list_doc_str)

with open("agent_prompt.py", "w", encoding="utf-8") as f:
    f.write(prompt_content)
