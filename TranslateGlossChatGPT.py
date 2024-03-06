# %% [markdown]
# # Translate Gloss by ChatGPT

# %%
import getpass, json, re, copy, os, time
from openai import OpenAI

# %%
# see if we can get an openai api key out of a config.json file
openai_api_key = None
if os.path.exists("config.json"):
    with open("config.json") as f:
        config = json.load(f)
        if "openai_api_key" in config:
            openai_api_key = config["openai_api_key"]

# %%
if not openai_api_key:
    openai_api_key = getpass.getpass("OpenAI api key?")

exclude_source_gloss = False
extra_ChatGPT_instructions = ""
# %%
# output_language = "Farsi"
# input_data = "./data/php_21.01.2024.json"
# output_filename = f"./data/php_ChatGPT_{output_language}.json"
# book_name = "Philippians"

# output_language = "English"
# input_data = "./data/tite21_21.01.2024.json"
# book_name = "Titus"

# output_language = "French"
# input_data = "./data/php_21.01.2024.json"
# book_name = "Philippians"
# exclude_source_gloss = True #Don't include the french when producing French.

# output_language = "Farsi"
# input_data = "./data/php_21.01.2024.json"
# book_name = "Philippians"
# extra_ChatGPT_instructions = "\n\nUse Christian words such as in Persion Old Version. Do not use Muslim words or Arabic words."


output_language = "French"
input_data = "./data/auto_11-philippians.json"
book_name = "Philippians"
exclude_source_gloss = True #Don't include the french when producing French.

# %%
input_data_basename = os.path.basename( input_data ).split(".")[0]
output_filename = f"./data/{input_data_basename}_ChatGPT_{output_language}.json"

# %%
system_message = f"""
You are a language professor preparing language material.  
You are translating subsections of Bible verses from Greek and French into {output_language}.
""".strip()
#model = "gpt-3.5-turbo"
#model = "gpt-4"
model = "gpt-4-1106-preview"


# %%
#go ahead and load the data.
with open( input_data ) as fin:
    data = json.loads( fin.read() )

# %%
def generate_prompt_string( _data, verse_index, chunk_index, _book_name ):
    verse = _data[verse_index]
    chunks = verse['chunks']
    chunk = chunks[chunk_index]
    sources = chunk['source']
    first_piece = sources[0]

    _n = '\n' #f-string objection < python 3.12

    result = f"""
Look at this verse:
```
{_book_name} {first_piece['cv']}: {verse['sourceString']}
```
""".lstrip()

    result += f"""
Focus on these specific words:
```
{' '.join(source['content'] for source in sources)}
```
"""

    if any( ('morph' in source) for source in sources ):
        result += f"""
Morphology information:
```
{_n.join( source['content'] + ': ' + ','.join(source['morph']) for source in sources if 'morph' in source) }
```
"""

    if not exclude_source_gloss:
        result += f"""
The gloss for this in French is:
```
{chunk['gloss']}
```
"""

    result += f"""
What is the gloss for these specific words in {output_language}?  Mark supplemental implicit words with *asterisks* in the gloss. Output the answer in JSON. {extra_ChatGPT_instructions}

Example output:
```json
{{"gloss": "combined-words and *implicit words* example"}}
```
"""
    return result.strip()

# %%
print( generate_prompt_string( data, 0, 0, book_name ) )

# %%
client = OpenAI( api_key = openai_api_key )
def generate_gloss_for( _data, verse_index, chunk_index, _book_name ):
    prompt = generate_prompt_string( _data, verse_index, chunk_index, _book_name )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
    )
    #return response.choices[0].text,
    return response

# %%

def extract_answer_from_response( _response, greek_sentence ):
    #This checks to see if it is in a MarkDown block.
    extractor_regular_expression = r"```(?:json)?(?P<json_data>.*?)```"
    match = re.search(extractor_regular_expression, _response.choices[0].message.content, re.DOTALL)

    if not match:
        #This one checks for just raw json
        extractor_regular_expression = r"(?P<json_data>\{.*\})"
        match = re.search(extractor_regular_expression, _response.choices[0].message.content, re.DOTALL)

        if not match:
            raise ValueError("Result not in expected format.")

    extracted_data = match.group('json_data')

    #now parse the json.
    response = json.loads(extracted_data)

    #see if we can find a reference to output_language
    for key, value in response.items():
        if output_language.lower() in key.lower():
            return value
        
    #see if the key "gloss" works.
    if 'gloss' in response:

        #make sure none of the greek made it into the output.
        for word in greek_sentence.split():
            if word in response['gloss']:
                raise ValueError("Greek word found in gloss.")

        return response['gloss']

    raise ValueError("Result not in expected format.")   


# %%
def number_of_verses( _data ):
    return len(_data)
def number_of_chunks( _data, verse_index ):
    return len(_data[verse_index]['chunks'])


# %%
output_data = copy.deepcopy(data)

verse_index = 0
chunk_index = 0

# %%
starting_time = time.time()

#append to process.log
with open( f"{input_data_basename}_{output_language}_process.log", "w" ) as process_out:
    done = False

    while not done:

        if verse_index >= number_of_verses(data):
            done = True

        if not done:
            try:
                process_out.write( f"Processing verse {verse_index} chunk {chunk_index}\n" )
                process_out.write( f"Prompt string:\n{generate_prompt_string( data, verse_index, chunk_index, book_name )}\n\n")

                response = generate_gloss_for( data, verse_index, chunk_index, book_name )

                process_out.write( f"Response:\n{response.choices[0].message.content}\n\n" )

                answer = extract_answer_from_response( response )

                process_out.write( f"Answer:\n{answer}\n\n" )
                process_out.flush()

                output_data[verse_index]['chunks'][chunk_index]['gloss'] = answer

                chunk_index += 1
                if chunk_index >= number_of_chunks(data, verse_index):
                    verse_index += 1
                    chunk_index = 0

                    now = time.time()
                    end_estimation_time = now + (now - starting_time) * (number_of_verses(data) - verse_index) / (verse_index)
                    print( f"Estimated end time: {time.strftime('%Y-%m-%d %I:%M:%S %p', time.localtime(end_estimation_time))}  Arrange count: {verse_index}/{number_of_verses(data)}" )

            #catch ValueError
            except ValueError as e:
                process_out.write( f"Error processing verse {verse_index} chunk {chunk_index}: {e}\n" )
                process_out.flush()
                time.sleep(10)


# %%
with open( output_filename, 'w' ) as result_file_out:
    result_file_out.write( json.dumps( output_data, indent=4, ensure_ascii=False  ) )

# %%



