# %%

input_files = "./data/*.json"

book_name_map = {
    "jud13.json": "Jude",
    "Mat67.json": "Matthew",
    "php_21.01.2024.json": "Philippians",
}

# %%

import json
import glob

# %%
def number_of_verses( _data ):
    return len(_data)
def number_of_chunks( _data, verse_index ):
    return len(_data[verse_index]['chunks'])


# %%

#iterate through input files using glob.
for input_file in glob.glob(input_files):
    if input_file in book_name_map:
        book_name = book_name_map[input_file]
    else:
        book_name = input_file.split("/")[-1].split(".")[0]

    with open(input_file) as fin:
        data = json.load(fin)

    print( f"Processing {input_file}" )
    output_file = input_file.replace(".json", ".html")



    with open(output_file, "w") as fout:
        done = False
        table_open = False
        verse_index = 0
        chunk_index = 0
        last_reference = ""

        fout.write( f"""
<html>
    <title>{output_file}</title>
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

                gloss_mapping = None
                if 'gloss_mapping' in chunk: 
                    gloss_mapping = chunk['gloss_mapping']

                if reference != last_reference:
                    if table_open:
                        fout.write("</table>\n")
                        table_open = False

                    fout.write("<hr>\n")
                    fout.write(f"<b>{reference}</b><br>\n")
                    fout.write(f"{verse_text}\n")


                    fout.write( "<table><tr><th>Greek</th><th>Gloss</th></tr>\n" )
                    table_open = True

                    last_reference = reference


                if not gloss_mapping:
                    greek_piece = ' '.join(source['content'] for source in sources)
                else:
                    greek_pieces_html = []
                    for index, source in enumerate(sources):
                        morphology_title = f"{source['content']} ({','.join(source['morph'])})".replace( '"', '&quot;' ).replace( "'", '&apos;' )
                        greek_pieces_html.append( f"<span class='{colors[index % len(colors)]}' title='{morphology_title}'>{source['content']}</span>" )
                    greek_piece = ' '.join(greek_pieces_html)

                if not gloss_mapping:
                    output_piece = chunk['gloss']
                else:
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

                #fout.write(f"<li>{greek_piece} - {output_piece}</li>")
                #fout.write(f"<li style='display: flex; justify-content: space-between;'>{greek_piece} - {output_piece}</li>")
                fout.write( f"<tr><td>{greek_piece}</td><td>{output_piece}</td></tr>\n" )


                chunk_index += 1
                if chunk_index >= number_of_chunks(data, verse_index):
                    verse_index += 1
                    chunk_index = 0
        
        if table_open:
            fout.write("</table>\n")
            table_open = False
        fout.write("</body></html>\n")


# %