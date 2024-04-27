
# %%
import glob
import os
import re
import json
from collections import defaultdict

# %%

input_file_filter = "auto_\\d+-([^_]+).json"
directory_structure = "/data/auto_just_greek/{book}/{chapter}.html"

def collect_files( input_folder, input_file_filter ):
    pattern = re.compile(input_file_filter)
    files = sorted(
        os.path.join(input_folder, filename)
        for filename in os.listdir(input_folder)
        if pattern.match(filename)
    )

    filename_to_json = {}
    for file in files:
        filename = os.path.basename( file )
        with open( file, 'r' ) as fin:
            filename_to_json[filename] = json.load( fin )

    return filename_to_json

# %%
def index_files_into_book_chapter_verse( filename_to_json ):
    pattern = re.compile(input_file_filter)
    book_chapter_verse_to_sentence = defaultdict( lambda: defaultdict( lambda: defaultdict( list ) ) )

    for filename, data in filename_to_json.items():
        #use the capture group in input_file_filter to get the book name from the filename.
        match = pattern.match(filename)
        if match:
            book_name = match.group(1)

            for sentence in data:
                first_chunk = sentence['chunks'][0]
                
                chapter,verse = map(int,first_chunk['source'][0]['cv'].split(':'))

                book_chapter_verse_to_sentence[book_name][chapter][verse].append(sentence)

    return book_chapter_verse_to_sentence
def number_of_sentences( _data ):
    return len(_data)
def number_of_chunks( _data, verse_index ):
    return len(_data[verse_index]['chunks'])
# %%
def generate_output_files( book_chapter_verse_to_sentence ):
    for book_name, chapter_verse_to_sentence in book_chapter_verse_to_sentence.items():
        for chapter_number, verse_to_sentence in chapter_verse_to_sentence.items():
            #we have a page per chapter.
            abs_output_filename = directory_structure.format( book=book_name, chapter=chapter_number )
            output_filename = f".{abs_output_filename}"
            #create missing folders.
            os.makedirs(os.path.dirname(output_filename), exist_ok=True)

            with open( output_filename, 'w' ) as fout:
                fout.write( f"<html><head><title>{book_name} {chapter_number}</title>\n" )

                fout.write( """
<meta charset="UTF-8"> <!-- Set character encoding to UTF-8 -->
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
/* https://alistapart.com/article/horizdropdowns/ */
/*ul {
 margin: 0;
 padding: 0;
 list-style: none;
 width: 150px;
}

ul li {
 position: relative;
}

li ul {
 position: absolute;
 left: 149px;
 top: 0;
 display: none;
}
ul li a {
 display: block;
 text-decoration: none;
 color: #777;
 background: #fff;
 padding: 5px;
 border: 1px solid #ccc;
 border-bottom: 0;
}
/* Fix IE. Hide from IE Mac */
* html ul li { float: left; }
* html ul li a { height: 1%; }
/* End */
ul {
 margin: 0;
 padding: 0;
 list-style: none;
 width: 150px;
 border-bottom: 1px solid #ccc;
}
li:hover ul { display: block; } */

ul {
  margin: 0;
  padding: 0;
  list-style: none;
  width: 150px;
}

ul li {
  position: relative;
}

li ul {
  position: absolute;
  left: 100%; /* Adjust the position relative to the parent li */
  top: 0;
  display: none;
}

ul li a {
  display: block;
  text-decoration: none;
  color: #777;
  background: #fff;
  padding: 5px;
  border: 1px solid #ccc;
  border-bottom: 0;
}

ul {
  margin: 0;
  padding: 0;
  list-style: none;
  width: 150px;
  border-bottom: 1px solid #ccc;
}

li:hover ul {
  display: block;
}



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

  /* Style for the menu */
  .menu {
    width: 200px; /* Adjust width as needed */
    float: left;
    background-color: #f0f0f0;
    padding: 20px;
  }

  /* Style for the content */
  .content {
    margin-left: 220px; /* Make space for the menu */
    padding: 20px;
  }

</style>
                """.strip() )


                fout.write( "</head><body>\n")

                prev_link = None
                next_link = None

                last_other_was_current = False
                last_other_link = None

                #write a menu structure. https://alistapart.com/article/horizdropdowns/
                fout.write( "<ul class=\"menu\">\n" )
                for other_book_name, other_chapter_verse_to_sentence in book_chapter_verse_to_sentence.items():
                    fout.write( f" <li class=\"menu_item\"><a href=\"#\">{other_book_name}</a>\n" )
                    fout.write( f"  <ul class=\"submenu\">\n" )
                    for other_chapter, other_verse_to_sentence in other_chapter_verse_to_sentence.items():
                        other_filename = directory_structure.format( book=other_book_name, chapter=other_chapter )
                        fout.write( f"   <li class=\"submenu_item\"><a href=\"{other_filename}\">{other_chapter}</a></li>\n" )

                        if other_book_name == book_name and other_chapter == chapter_number:
                            prev_link = last_other_link
                            last_other_was_current = True
                        else:
                            if last_other_was_current:
                                next_link = f"<a href=\"{other_filename}\">{other_book_name} {other_chapter} -&gt;</a>"
                            last_other_was_current = False
                        last_other_link = f"<a href=\"{other_filename}\">&lt;- {other_book_name} {other_chapter}</a>"

                    fout.write( f"  </ul></li>\n" )
                fout.write( "</ul>\n" )

                fout.write( "<div class=\"content\">\n" )

                if prev_link:
                    fout.write( f"<p>{prev_link}</p>\n" )

                # for verse, sentence in verse_to_sentence.items():

                #     fout.write( f"<p>{verse} {sentence}</p>\n" )

                done = False
                table_open = False
                sentence_index = 0
                chunk_index = 0
                last_reference = ""
                last_sentence_text = ""


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

                data = []
                for verse in verse_to_sentence.values():
                    for sentence in verse:
                        data.append(sentence)

                while not done:

                    if sentence_index >= number_of_sentences(data):
                        done = True

                    if not done:

                        sentence = data[sentence_index]
                        chunks = sentence['chunks']
                        chunk = chunks[chunk_index]
                        sources = chunk['source']
                        first_piece = sources[0]

                        reference = f"{book_name} {first_piece['cv']}"
                        sentence_text = f"{sentence['sourceString']}".replace( "'", "&apos;" ).replace( '"', "&quot;" ).replace( "<", "&lt;" ).replace( ">", "&gt;" )

                        gloss_mapping = None
                        if 'gloss_mapping' in chunk: 
                            gloss_mapping = chunk['gloss_mapping']


                        if reference != last_reference:
                            if table_open:
                                fout.write("</table>\n")
                                table_open = False

                            if sentence_text != last_sentence_text:
                                fout.write( "<hr>\n" )
                                fout.write( sentence_text )
                                last_sentence_text = sentence_text
                            fout.write( f"<hr><b>{reference}</b><br><hr>\n" )


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

                        #file_out.write(f"<li>{greek_piece} - {output_piece}</li>")
                        #file_out.write(f"<li style='display: flex; justify-content: space-between;'>{greek_piece} - {output_piece}</li>")
                        fout.write( f"<tr><td>{greek_piece}</td><td>{output_piece}</td></tr>\n" )


                        chunk_index += 1
                        if chunk_index >= number_of_chunks(data, sentence_index):
                            sentence_index += 1
                            chunk_index = 0
                
                if table_open:
                    fout.write("</table>\n")
                    table_open = False


                if next_link:
                    fout.write( f"<p>{next_link}</p>\n" )

                fout.write( "</div>\n" )

                fout.write( """
<script>
document.addEventListener('DOMContentLoaded', function () {
  var menuItems = document.querySelectorAll('.menu_item');


  console.log( "running menu items" );

  menuItems.forEach(function (menuItem) {
    console.log( "running menu item " + menuItem );

    menuItem.addEventListener('click', function (event) {
      var submenu = menuItem.querySelector('ul');
      if (submenu) {
        //event.preventDefault(); // Prevent default link behavior
        submenu.classList.toggle('show'); // Toggle the 'show' class to display/hide submenu
      }
    });
  });
});
</script>
                """.strip())

                fout.write( "</body></html>\n" )
# %%
test = collect_files( "./data", input_file_filter )
indexed_test = index_files_into_book_chapter_verse( test )
generate_output_files( indexed_test )
# %%

#TODO fix it so that you can select even without a scroll wheel if the sub menu goes off the bottom of the page.
#     I should probably do this by getting rid of the cool over menu and just make it so that you have the chapters of the current book across the top.
#     Make it so that the current chapter is bolded or something.