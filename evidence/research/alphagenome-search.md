# Search

[Search v0.5.6 released 2020-02-24](https://github.com/arXiv/arxiv-search/releases)

Search term or terms

FieldAll fieldsTitleAuthor(s)AbstractCommentsJournal referenceACM classificationMSC classificationReport numberarXiv identifierDOIORCIDLicense (URI)arXiv author IDHelp pagesFull text

Search

Show abstracts
Hide abstracts


[Advanced Search](https://arxiv.org/search/advanced?terms-0-term=AlphaGenome+single+nucleotide+variant+genomics+deepmind&terms-0-field=all&size=50&order=-announced_date_first)

Sorry, your query for all: AlphaGenome single nucleotide variant genomics deepmind produced no results.


#### Searching by Author Name

- Using the **Author(s) field** produces best results for author name searches.
- For the most precise name search, follow **surname(s), forename(s)** or **surname(s), initial(s)** pattern: example Hawking, S or Hawking, Stephen
- For best results on multiple author names, **separate individuals with a ;** (semicolon). Example: Jin, D S; Ye, J
- Author names enclosed in quotes will return only **exact matches**. For example, "Stephen Hawking" will not return matches for Stephen W. Hawking.
- Diacritic character variants are automatically searched in the Author(s) field.
- Queries with no punctuation will treat each term independently.

#### Searching by subcategory

- To search within a subcategory select **All fields**.
- A subcategory search can be combined with an author or keyword search by clicking on **add another term** in advanced search.

## Tips

Wildcards:

- Use ? to replace a single character or \* to replace any number of characters.
- Can be used in any field, but not in the first character position. See Journal References tips for exceptions.

Expressions:

- TeX expressions can be searched, enclosed in single $ characters.

Phrases:

- Enclose phrases in double quotes for exact matches in title, abstract, and comments.

Dates:

- Sorting by announcement date will use the year and month the _original version_ (v1) of the paper was announced.
- Sorting by submission date will use the year, month and day the _latest version_ of the paper was submitted.

Journal References:

- If a journal reference search contains a wildcard, matches will be made using wildcard matching as expected. For example, **math\*** will match _math_, _maths_, _mathematics_.
- If a journal reference search does **not** contain a wildcard, only exact phrases entered will be matched. For example, **math** would match _math_ or _math and science_ but not _maths_ or _mathematics_.
- All journal reference searches that do not contain a wildcard are literal searches: a search for **Physica A** will match all papers with journal references containing _Physica A_, but a search for **Physica A, 245 (1997) 181** will only return the paper with journal reference _Physica A, 245 (1997) 181_.

[Search v0.5.6 released 2020-02-24](https://github.com/arXiv/arxiv-search/releases)