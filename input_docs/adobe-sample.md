# Introduction

In this tutorial, we will delve into the structure, deployment, and execution of a sample output in the form of a PDF file, complete with bookmarks. This PDF is segmented into eight distinct pages, each representing a unique section of the data.

## Understanding the Sample Output

The sample output is a PDF file that incorporates bookmarks, dividing it into eight separate sections. Each section offers a distinct view of the data, such as invoices categorized by date, item type, or transaction amount.

## Overview of the Sample Output Files

The sample output comprises several files, each playing a critical role in the generation and display of the PDF:

- `ap_bookmark.IFD`
- `ap_bookmark.mdf`
- `ap_bookmark.dat`
- `ap_bookmark.bmk`
- `ap_bookmark.pdf`
- `ap_bookmark_doc.pdf`

## Deploying and Running the Sample Output

To deploy and run the sample output, adhere to the steps detailed in the following sections.

# Sample Output Overview

The sample output is a PDF file with bookmarks, divided into eight separate pages. Each page represents a different section of the data, offering a unique perspective.

# Sample Output Description

The PDF file is generated based on a data file containing eight records. Each record corresponds to a specific section of the PDF, such as invoices by date, item type, or transaction amount.

# Bookmark File Sections

The sample output PDF is divided into three bookmark sections:

1. **Invoices by Date**
   - This section organizes invoices based on their date.

2. **Invoices by Item Type**
   - This section categorizes invoices according to the type of items they contain.

3. **Invoices by Transaction Amount**
   - This section sorts invoices based on the total transaction amount.

# Sample Output Files

The sample output consists of the following files:

- `ap_bookmark.IFD`: The index file for the PDF.
- `ap_bookmark.mdf`: The metadata file for the PDF.
- `ap_bookmark.dat`: The data file containing the records for each section.
- `ap_bookmark.bmk`: The bookmark file for the PDF.
- `ap_bookmark.pdf`: The generated PDF file.
- `ap_bookmark_doc.pdf`: A documentation PDF file.

# Deploying the Sample Output

To deploy the sample output, follow these steps:

1. Open `ap_bookmark.IFD` in Output Designer.
2. Adjust the `-z` option in the `^job` command within `ap_bookmark.dat`.
3. Position the files in their respective directories.

# Running the Sample Output

To execute the sample output, follow these steps:

1. Position `ap_bookmark.dat` in the collector directory scanned by Central.
2. Utilize command line parameters to specify the desired bookmark section.

# Conclusion

By comprehending the structure and deployment of the sample output, you can effectively generate and utilize PDF files with bookmarks for various data perspectives.