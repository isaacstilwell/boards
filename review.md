Who reviewed your code / when?: Chi Zhang, 5/18

Link to the git commit and files in question (be sure to include the git commit hash to denote the specific version of the project reviewed)
[Commit](https://github.com/isaacstilwell/boards/commit/6416555032eae099eafed4b2fc031c6de8ebaf16) - specficially scraper files (base, ckscraper, dkscaper, ghscraper, nkscraper, helpers)

Provide your reviewer with 2-3 questions you'd like them to focus on, and include those here.

- How can I improve the readability of my scraper code?
- Do you find the logic of the date parsing to be sound? Are there things I can improve?

Provide your reviewer's responses.

- How can I improve the readability of my scraper code?
    - Comments on the top of each file describing what each class does can give readers more context, improving readability
    - Creating a `results` dict that holds results, and having each parser return
        `ScrapedThread(**results)`
        may improve readability
    - Having a base class that describes how all the parsers should act is a great touch! Helps readability a lot
- Do you find the logic of the date parsing to be sound? Are there things I can improve?
    - I wonder if there's an external library that can help parse dates from websites, but that may be wishful thinking
    - Having your own custom date class with a custom dunder for `if not ...` could help readability but that's a QOL change
    - It's impressive how many types of date formats your code covers! Date parsing from websites seems really annoying to deal with
        and your code is very impressive to read through

Have a discussion about the code in question and include any other notes/things that you learned from the review.
- Talked about challenges involved in web scraping, why there needs to be a subclass of the base scraper for every site
- Chi suggested and showed some basic code for creating a custom date class that could abstract some of the code in helpers/extract_dates
- Also suggested doing some documentation of the scrapers and the sites at the top of each scraper doc

What, if any, changes did this review lead to you making to your code.
- Add documentation for each scraper subclass
- ~~Add custom date class in helpers/extract_dates~~ (rejected - this isn't helpful with two separate date paths)
- ~~Implement results dict idea in scrapers~~ (rejected - this adds more code with no meaningful readability changes)
