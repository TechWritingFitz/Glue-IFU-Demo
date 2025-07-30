# Glue - Developer Documentation #

## Overview ##

This document serves as the business case and technical overview for Glue, a full-stack web application developed to centralize, automate and archive technical content relating to Instructions for Use documentation at LetsGetChecked.

## Business case for the tool's development ##

As a result of it's rapid financial expansion over the course of the COVID-19 pandemic, LetsGetChecked's operations had to be capable of supplying test kits at greater volumes to a longer client list than at any previous point in it's history. This rapid scaling of operations proved challenging from a number of perspectives, not least in its management and development of the technical content that shipped with each of its test kits. This included warnings, advisories and instructions for use.

While operating at a start-up, the company could afford to operate on the principle of its solutions and approaches being just about "good enough", to meet the deadline, ship the kits, and so forth. However, with a greater number of clients came greater demands for content to be at hand in a way that was accurate, intuitive and predictable. This was not the case, with technical content spread across numerous Jira tickets, PDFs, excel spreadsheets, google docs and Quality Management Systems (QMS).

What we needed was a structured CMS, such as Paligo or MadCapFlare, to centralize the content repository. However, given that a CMS (Contentful) had already been purchased, and the cost of a structured CMS was estimated to be €90,000 per annum (estimate provided by pre-sales call research), this was not viable.

As a result, I set about using pre-existing knowledge of software development, coding and mark-up languages, and the company's chosen LLM (Gemini) to create our own, internal tool from scratch. The aim was to build this tool to manage our content in relation to the **FAIR** principles for scientific data management and stewardship, which were published in the journal *Scientific Data* in 2016. FAIR is an acronym for the following principles:

- *Findable*: Metadata and data should be easy to find for both humans and computers. Machine-readable metadata are essential for automatic discovery of datasets and services.

- *Accessible*: Once found, data should be stored and presented in such a way that they can be accessed via formal authentication and authorisation processes.

- *Interoperable*: The data is integrated with other data, applications and workflows for ease of analysis, storage and processing.

- *Reusable*: The data should be reused as widely as is appropriate, and described as fully as possible so that they can be replicated and/or combined in a range of settings.

## Technical specification: iterative development ##

### 1. Prove basic find and retrieve function using Python and SQL database ###

The first step in Glue's creation was to find and retrieve our pre-existing content from its current locations, and convert that content into strings of text that could be stored in a sql database and queried using Python commands. I took a sample of 17 IFU documents, and manually inputted their text content into a well-organised spreadsheet, which was structured so as to be readable by Python scripts. My intention here was two-fold:

1. to prove that I could create a SQL database derived from this basic structure

2. that I could find and retrieve the content from the spreadsheet's tables using a Python script.

I achieved both of these aims through successfully running the `SQL_IFUQueryBase_StringExtraction.py` file.

### 2. Prove text extraction from pre-existing PDF corpus ###

Step 1 was useful as a proof of concept and confidence-building exercise. However, manual data entry was both time-consuming and error-prone. I knew I had to work out a way of taking the overall corpus of instructional and regulatory language that constitutes our Instructions for Use documentation, and extracting its text automatically and at scale. The current corpus is decentralized across dozens of individual PDFs, so I needed to write a script that would successfully and efficiently extract that text from its PDF template, and save it in a format that was useful for access through a web-based UI. To this end, I decided on JSON. I then set about working with Gemini to iterate through approaches to extracting the text as needed.

#### Iteration 1: Initial Text Extraction & Problem Identification ####

**Action:** We began with a simple script using `page.get_text()` to extract all text from a PDF page.

**Observation:** This successfully extracted the text characters but resulted in a jumbled, unordered block of content.

**Diagnosis:** The default extraction method does not respect the visual reading order of the document, especially with multi-column layouts.

#### Iteration 2: Block-Level Sorting ####

**Action:** We refined the script to use `page.get_text("blocks")`, which extracts text in chunks along with their coordinates. We then sorted these blocks by their vertical and horizontal positions.

**Observation:** The order improved but was still jumbled. Text from different logical "panels" of the accordion fold was being interleaved.

**Diagnosis:** The sorting logic was too simple for the accordion layout. It was correctly reading left-to-right across the entire page at each vertical level, mixing content from different panels.

#### Iteration 3: Word-Level Extraction (The "All Content" Test) ####

**Action:** To ensure no text was being missed, we moved to the most granular level using `page.get_text("words")` and looped through all pages of the document.

**Observation:** The resulting text file successfully contained all the text from the document, including previously missing sections from later pages. However, the order was still completely jumbled.

**Diagnosis:** This confirmed two things: 1. We could access all the necessary content. 2. A simple sorting key is insufficient; we need a layout-aware approach.

#### Iteration 4: The "Panel Slicing" Logic ####

**Action:** We designed the final parsing strategy. This involved creating a `PANEL_LAYOUT` dictionary in the script to define the precise coordinate boundaries for each logical panel of the document. The script's logic was rewritten to:

- Extract all individual words and their coordinates.
- Assign each word to a specific panel by checking if its coordinates fall within that panel's defined boundaries.
- Separate the words within each panel into English and Spanish columns.
- Sort the words within each column to reconstruct the final, clean text.

**Observation:** Initial tests with an incorrectly configured `PANEL_LAYOUT` resulted in empty or jumbled panels, proving the importance of accurate coordinates.

#### Iteration 5: The Visual Debugger Tool ####

**Action:** To solve the difficulty of manually defining panel coordinates, we created a separate utility script, `visual_debugger.py`.

**Observation:** This script reads the `PANEL_LAYOUT` dictionary and draws colored rectangles directly onto a copy of the PDF, providing instant visual feedback on whether the defined boundaries are correct.

**Diagnosis:** This tool was identified as the key to allowing for accurate configuration of the main parsing script.

#### Iteration 6: Handling for English vs Spanish panels and differing panel orientations ####

**Action:** We used the visual debugging script to successfully render each of the English language panels. However, two bugs emerged from this process:

**Observations:**

1. In the JSON output, the English language was appearing under the Spanish language heading.

2. The third panel was still producing jumbled output, due to the fact that its geometric orientation was landscape rather than portrait.

**Diagnosis:** In order to handle these new bugs, we declared the language type per panel under the configuration section of the script and then declared the orientation of each panel in the script's panel dictionary.

#### Iteration 7: test the script for handling greater numbers of IFU content ####

**Action:** Beyond proof of concept on one IFU, the extraction script started to fail on an expanded list of eight IFU documents from which I asked it to extract text. Failure rate was 50%, with the JSON file to which the text was saved containing four cases of jumbled IFU content that did not match the original source document.

**Observation:** The cause of these failures was simple: the script needed to be modified to handle slight differences in layout across the corpus as a whole. Within our IFU corpus, we have a range of layouts that structure the presentation of our content in PDF format. The maximum number of panels in one of these documents is 26 (24 regulatory and instructional panels, plus two metadata panels). The minimum number of panels is 8, which are the IFUs for our genetic screening tests. Due to the consumables used in these kits, we do not include any sample collection instructions in the document, hence the smaller number of panels. In between these parameters are groups of IFUs carrying 10,12, 14, 18 and 22 panels respectively, with two sub-types for fourteen panel IFUs. This amounts to eight possible layouts for each IFU that we ship.

**Diagnosis:** I have since compiled a JSON layout file per each of these layouts, and run the extraction script on sample PDFs. The text is compiling successfully into an output JSON file; this should mean each IFU that falls into one of the layout types compiles successfully, too. There are bugs that need handling as follows:

1. English language sometimes compiles into Spanish rows within the JSON output file, and vice versa.

2. When regulatory language panels are read by the script as stands, it doesn't handle for the columns into which the text is arranged. As a result, the text is jumbled in the output file.

### 3. Connect extracted JSON files with the Glue Database ###

In order to store the extracted JSON content in the Glue database, we created a Python script to read each of the PDFs currently in the project's directory through the lens of the layout templates that we devised through iterations 3-7. The script created a dictionary called `LAYOUT_MAPPING`, which acted as the source of reference when the script was reading through the stack of PDFs. The script then ran an intialization command for the database `def initialize_database():`, and created the following series of tables:

```sql
-- Table 1: IFU Documents
CREATE TABLE IF NOT EXISTS ifu_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_number TEXT NOT NULL,
    document_version TEXT NOT NULL,
    language TEXT NOT NULL,
    source_filename TEXT,
    created_at TIMESTAMP,
    UNIQUE(part_number, document_version, language)
);```

# Add metadata columns if they don't exist
```python
meta_columns = ['sample_type', 'market', 'dispatch_code', 'kit_code', 'consumables', 'stability_type', 'biomarkers']
for column in meta_columns:
    try:
        cursor.execute(f'ALTER TABLE ifu_documents ADD COLUMN {column} TEXT')
        print(f"  -> Added column '{column}' to 'ifu_documents'.")
    except sqlite3.OperationalError:
        pass # Column already exists```

```sql
-- Table 2: Content Panels
CREATE TABLE IF NOT EXISTS content_panels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    panel_number INTEGER NOT NULL,
    panel_type TEXT,
    content_text TEXT,
    content_hash TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES ifu_documents (id)
);```

```sql
-- Table 3: IFU Requests (for NPI workflow)
CREATE TABLE IF NOT EXISTS ifu_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_type TEXT NOT NULL,
    status TEXT NOT NULL,
    part_number_to_update TEXT,
    sample_type TEXT,
    biomarkers TEXT,
    stability_period TEXT,
    consumables TEXT,
    market TEXT,
    created_by TEXT,
    created_at TIMESTAMP
);```

```sql
-- Tables for Users and Roles
CREATE TABLE IF NOT EXISTS roles (id INTEGER PRIMARY KEY, role_name TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, role_id INTEGER, FOREIGN KEY(role_id) REFERENCES roles(id));
```

This was the origin of the database's functionality as a web application, as we began thinking about how to surface information from the IFUs accurately. The next step was to install a Flask server and create a basic index page to act as a website, which could then be refined to promote appropriate and efficient user experiences.

There are still bugs to be fixed here: ligatures keep popping up as a hangover from the ingesting of the text from PDF design files. We have yet to figure out a way of removing these across the corpus as a whole. In addition, there are some warnings panels that still do not render properly, with text out of its correct grammatical order. I believe this is to do with the fact that additional panel layouts are needed, so that the layout dictionary in the DB upload script can read for subtleties in the layouts of warning panels in different IFUs.

### 4. Build out the Flask server and establish an index page for the website ###

We started a new .py script named `api_server`, which imported a range of server, directory and mark-up language libraries (jsonify, Flask, difflib, sqlite3) and allowed for the establishing of API endpoints to connect the database developed under Iteration 3 to speak to our index page on the website. Initially, these endpoints were limited to:

- a `GET` function to fetch a list of all unique IFU documents and their respective document IDs

- a `GET` function to fetch all content panels for a single IFU document within that list

- a `POST` function to search content panels for a given keyword using SQL queries

- a `POST` function to compare text with filtering across the IFU corpus

We then wrote the following boilerplate command to trigger the server to run when the Python script was executed:

```PYTHON
if __name__ == '__main__':
    app.run(debug=True, port=5001) # Or another port you chose
```

The creation of these APIs within the server decoupled the front- and back-ends from one another. This is important, as it allows for parallel development on the application's respective parts, depending on what they might need at a given time. For example, should the website start receiving a new, larger stream of traffic, the front-end can remain the same but the back-end might need to be developed to create further capacity to handle that uptick in traffic. Effectively, decoupling allows front- and back-end development teams to respond to the application's needs without getting in one another's way. A useful analogy here is that of a hospital, where specialized departments operate independently yet contribute to the overall organization's success, allowing for specialized operations but (at least theoretically) preventing interdependencies that result in bottlenecks.

### 5. Build functions that allow for comparison and version control of particular strings ###

With this full-stack architecture in place, we could then think more deeply about the UI and how changes to the UI/UX elements of the index page would change both it and the way in which the Flask server and database operated.

I knew that one of the core specifications for the app needed to be a comparison function. A critical weakness and risk to the way in which technical content gets managed in my current team is that no-one really knows with any objective degree of confidence which language we are using where, for how long, and why that language started to be used. Therefore, being able to compare that language across the corpus as developed to this point was very important.

#### Iteration 1: colored tiles, part numbers and percentages ####

The first version of this functionality was to have the metadata about each content panel presented in a tile under an Archive tab in the UI. These tiles were inlaid within the tab and contained a summary of the content, a percentage accuracy relative to other panels that appeared in different documents, and were color-coded through red, amber and green to match that percentage. The content's accuracy changed the tile's color, and then intensified the color the higher the percentage went within pre-ordained accuracy ranges. This worked well, but I found the tiles to be too busy and wanted to see more of the text.

#### Iteration 2: hover box with percentages and part numbers ####

We then developed a hover box UI, that carried the accuracy percentages and part numbers, but I still wanted to see more of the content.

#### Iteration 3: hover box with distinctions between language highlighted and specific differences called out in an ordered list ####

The current iteration declares the source panel in full at the top of a Comparison Results hover box. Where similar panels are found, the similarities and distinctions between them and the source panel are highlighted in yellow and green, and the overall similarly percentage is given in a rounded element to the right of the tile.

I think this functionality needs further refining, but I am basically happy with this layout. I want to protect this functionality while developing Glue's other features.

### 6. Additional functionality ###

At this point, I realised that Glue needed interfaces with documents that are adjacent to the IFUs that our team produces, namely Labelling Development Checklists and Bills of Materials. I'll say more about the labelling checklists below, because their role and signficance in the workflow comes after new content has been drafted. However, Bills of Material are a useful point of reference for drafting new content.

#### Bills of Materials ####

They contain long lists of which kit contents (also known as consumables, like test tubes and biohazard bags) ship with which IFU. They are central to determining which content appears in which IFU, and I wanted them to be front and centre as content was requested, drafted and approved.

The technical impact of ingesting this contextual information from the BOM was as follows:

A HTML form, with a file input command input `type='file'`. This allows users to select and upload an Excel file directly from their desktop. I had to debug this process, as the actual BOM was far too heavily formatted to allow for easy parsing into the app. Therefore, I manually copied the relevant consumable names and part numbers into a fresh spreadsheet for each of the IFUs. This is time-consuming, and might be revisited at a future date to see if we can automate this process.

A number of changes to the back-end:

A new API endpoint `(POST /API/upload_bom)`, created specifically to accept the file upload from the desktop.

The installation of the pandas library to parse the Excel file. This is important because it allows for the parsing of the spreadsheet's data into structured rows from which Python can read.

A new database table `bill_of_materials` was added to the database schema. Once the information from the spreadsheet is parsed into Python-readable format, the script iterates through it and inserts each item from the BOM as a new row in this table, linking it to a specific product or document.

There is an additional development project to be done here in surfacing relevant BOM data (consumables, kit codes, market) accurately throughout this workflow so that it is front and centre at each stage. However, so far, we have struggled to connect the back-end of the database successfully to each of the pages on the front end where this information appears. This is a crucial next step to upgrade the app's overall UX.

### 7.Develop requests, content creation and sign-off workflow ###

My next priority after developing the comparison function was to seal our current workflow for approving new content or updating pre-existing content off from the following risks:

1. Over-reliance on individual memory for locating and replicating the correct content.

2. Copying and pasting content between multiple file formats.

3. Incomplete context given as to which types of kit particular content will serve.

4. Transferring these files between multiple software platforms.

5. Each of these aspects of our current workflow contributes to the same group of recurrent problems:

6. Costly inaccuracies and errors making their way into printed IFUs

7. Heightened stress and low morale among contributing team members

8. An absence of version control over which content is included in regulatory and customer-facing documentation

To reduce the impact of these risks and problems, we created three new tabs in the UI titled:

- Requests

- Content Creation

- Checklist Review

#### Requests ####

The purpose of Requests is to receive the content of Jira tickets via a webhook from the NPI team on Jira. This necessitated creating a new `api/webhooks` endpoint in the Flask server .py file, and simulating the receipt of tickets through a curl command. Curl commands work with the URL generated by the Flask server, and a tunnelling server app named NGrok, to simulate the receipt of workflows from Jira. We currently don't have the administrative permissions to access the back-end of Jira boards, and so needed a way of testing the function while waiting to be granted these permissions. We created new user names in the relevant DB table and then pulled these into the UI via a JSON file, the contents of which were read and transmitted to the UI via the curl command.

#### Content Creation ####

The purpose of Content Creation was to allow medical writers to respond to these requests by either:

- finding pre-existing content
OR
- creating new content with an in-built word processor

At the front-end, this functionality necessitated the creation of a new HTML form, where writers could select a request and document template, and be automatically carried onto the Content Creation tab. JavaScript was also added to record the user's selections and send them to a new backend endpoint using a `POST` request. This was essentially given over to creating a new document using the selected data.

In the back-end, new database tables were added to store the document templates and their associated content sections. An additional API endpoint received the request from the front-end and took several, consequent actions:

- Fetched the request details

- Retrieved the document template from the new tables

- Merged the Jira data into the template

- Saved this newly generated, populated document as a record in the database and attached a "pending review" status to it

These changes allow medical writers to queue a template for review by the regulatory team, as part of the labelling development procedure that is triggered each time an IFU is requested to be created or updated from the NPI team. Creating templates in this way centralizes their creation process, and eradicates the need to copy and paste content between several different platforms.

Additional functionality is needed here to log the creation of new content in the database. It should be time-stamped with the writer who created it and, once the checklist, has been approved by regulatory specialists, the writers should receive a notification to justify the creation of this new content.

#### Checklist Review ####

The template created by the medical writers gets sent to the third and final tab, which is where regulatory specialists can sign-off on the selected content. Creating this tab necessitated a number of changes to the stack's structure:

- Front-end changes

- The creation of the page itself

- A JavaScript function to fetch a specific draft document from the back-end using its unique ID.

The rendering of that document as a checklist, which was color-coded in the UI to be yellow for "waiting for review" and green for "review complete". A "submit checklist" button was then added, which activated when all panels had turned green.

##### Back-end changes #####

Two new endpoints were added to the Flask server's functionality:

New API endpoint `(GET /api/document/id)`, which was created to retrieve the draft document.

New API endpoint `(POST /api/document/id/approve)`, which was created to allow the front-end to change the document's status from pending review to approved in the relevant database table.

This set of architectural decisions effectively transformed the stack from a relatively simple find, retrieve and compare documentation tool into a sophisticated workflow management tool, which integrated with Jira and then supported a centralized process for signing off on new iterations of content per particular types of test kit. In the process the stack evolved to support user input, document content creation triggers, and tailor the user interface for review processes by regulatory specialists.

## Key takeaways to date ##

Glue is now a working prototype internally within LetsGetChecked, and is due for presentation at the Product team's townhall in the next fortnight. It is available for access through an NGrok staging server connection on request. Glue's development has been instructive for understanding some key aspects of software development for documentation problems:

1. It is important to understand how the format of a document impacts the ways in which text can be extracted from it. The most challenging aspects of the tool's development so far was in arriving at the methodology for extracting text from heavily formatted and complex PDF templates. Obtaining the coordinates and temporarily storing the strings as JSON, before securing it in the SQL database, was a game changer for the app's development.

2. When comparing Glue's potential to our current workflow, it is striking how much easier and more efficient a centralized repository for managing this sort of content. This is particularly important in such a heavily regulated industry as medical devices, which does not demand technical writers and regulatory specialists to continually write creatively, but think well about how to manage the many different locations in which the same content appears.

3. The future impact of the tool is substantial, with financial savings of €100,000 per year over our current workflows and approaches. This has been calculated on the basis of costs arising from wasted print runs of incorrect IFUs (2 examples in 2 years, at a cost of €20-30,000 each), plus the costs associated with highly-trained staff spending excessive amounts of time finding, retrieving and reusing content manually. In addition, it derisk the business from non-compliance investigations and audit sanctions, and promotes user safety by ensuring the right content appears in the right places for particular patient populations.
