Who reviewed your code / when?: Chi Zhang, 5/18

Link to the git commit and files in question (be sure to include the git commit hash to denote the specific version of the project reviewed)

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

What, if any, changes did this review lead to you making to your code.
