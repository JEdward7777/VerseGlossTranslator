# %%

input_files_array = [ {
    "filename": "./data/php_21.01.2024.json",
    "title": "French"
},{
#     "filename": "./data/php_OpenHerm_English.json",
#     "title": "OpenHermes English",
# },{
    "filename": "./data/php_ChatGPT_English.json",
    "title": "ChatGPT English",
},{
    "filename": "./data/php_ChatGPT_English_matched.json",
    "title": "ChatGPT English (matched)",
},{
    "filename": "./data/php_ChatGPT_Spanish.json",
    "title": "ChatGPT Spanish",
},{
    "filename": "./data/php_ChatGPT_Russian.json",
    "title": "ChatGPT Russian",
}]
book_name = "Philippians"
output_filename = f"./data/Combined_output_for_{book_name}.html"

# %%

import json
import glob

# %%
def number_of_verses( _data ):
    return len(_data)
def number_of_chunks( _data, verse_index ):
    return len(_data[verse_index]['chunks'])


# %%

for input_config in input_files_array:
    with open(input_config['filename'],"r") as fin:
        input_config['data'] = json.load(fin)
        

with open(output_filename, "w") as fout:
    done = False
    table_open = False
    verse_index = 0
    chunk_index = 0
    last_reference = ""
    last_verse_text = ""

    fout.write( f"""
<html>
<title>{output_filename}</title>
""".strip() )
    
    fout.write( """
<style>
    /* Internal CSS */
    .navy-blue { color: navy; }
    .forest-green { color: forestgreen; }
    .burgundy { color: #800020; }
    .goldenrod { color: goldenrod; }
    .slate-gray { color: slategray; }
    .deep-purple { color: #36013F; }
    .teal { color: teal; }
    .maroon { color: maroon; }
    .olive-green { color: olive; }
    .royal-blue { color: royalblue; }
</style>
</head>
<body>
""".strip() )
    colors = [
        "navy-blue",
        "forest-green",
        "burgundy",
        "goldenrod",
        "slate-gray",
        "deep-purple",
        "teal",
        "maroon",
        "olive-green",
        "royal-blue",
    ]
    
    while not done:
        data = input_files_array[0]['data']
        if verse_index >= number_of_verses(data):
            done = True

        if not done:
            verse = data[verse_index]
            chunks = verse['chunks']
            chunk = chunks[chunk_index]
            sources = chunk['source']
            first_piece = sources[0]

            reference = f"{book_name} {first_piece['cv']}"
            verse_text = f"{verse['sourceString']}"

            if reference != last_reference:
                if table_open:
                    fout.write("</table>\n")
                    table_open = False

                if verse_text != last_verse_text:
                    fout.write( "<hr>\n" )
                    fout.write( f"{verse_text}")
                    last_verse_text = verse_text
                fout.write( f"<hr><b>{reference}</b><br><hr>\n" )

                fout.write( "<table><tr><th>Greek</th>")
                for input_config in input_files_array:
                    fout.write( "<th>" + input_config['title'] + "</th>" )
                fout.write( "</tr>\n" )
                table_open = True

                last_reference = reference


            greek_pieces_html = []
            for index, source in enumerate(sources):
                morphology_title = f"{source['content']} ({','.join(source['morph'])})".replace( '"', '&quot;' ).replace( "'", '&apos;' )
                greek_pieces_html.append( f"<span class='{colors[index % len(colors)]}' title='{morphology_title}'>{source['content']}</span>" )
            greek_piece = ' '.join(greek_pieces_html)


            fout.write( "<tr><td>" + greek_piece + "</td>" )

            for input_config in input_files_array:
                gloss_mapping = None
                data = input_config['data']
                chunk = data[verse_index]['chunks'][chunk_index]

                if 'gloss_mapping' not in chunk:
                    output_piece = chunk['gloss']
                else:
                    gloss_mapping = chunk['gloss_mapping']
                    output_pieces_html = []
                    for target, sources in gloss_mapping.items():
                        
                        title_tag = ""
                        if 'gloss_debug' in chunk and target in chunk['gloss_debug']:
                            source_escaped = chunk['gloss_debug'][target].replace('<','&lt;').replace('>','&gt;').replace('"','&quot;').replace( "'", '&apos;' )
                            title_tag = f" title=\"{source_escaped}\""


                        target_word = target.split(":")[1].strip()
                        if sources:
                            source = sources[0] #can't color it multiple colors so just take the first color.
                            source_index = int(source.split(":")[0].strip())
                            output_pieces_html.append( f"<span class='{colors[source_index % len(colors)]}'{title_tag}>{target_word}</span>" )
                        else:
                            output_piece = f"<i>{target_word}</i>"
                            if title_tag:
                                output_piece = f"<span{title_tag}>{output_piece}</span>"
                            output_pieces_html.append( output_piece )
                    output_piece = ' '.join( output_pieces_html )
                fout.write( f"<td>{output_piece}</td>" )
            fout.write( "</tr>\n" )


            data = input_files_array[0]['data']

            chunk_index += 1
            if chunk_index >= number_of_chunks(data, verse_index):
                verse_index += 1
                chunk_index = 0
    
    if table_open:
        fout.write("</table>\n")
        table_open = False
    fout.write("</body></html>\n")


# %