[DEBUG] __name__=__main__
[DEBUG] sys.argv=['src/main.py', 'https://www.adobe.com/support/products/enterprise/knowledgecenter/media/c4611_sample_explain.pdf']
[DEBUG] BOTTLE_CHILD=None
[DEBUG] Bottle is available
[Parser] Docling import successful.
[Analyzer][WARNING] Failed to import GraniteVision from beeai_framework adapters.
[Analyzer][WARNING] Vision capabilities may be unavailable or require a different import path.
[DEBUG] USE_MOCK_MODELS=False
[DEBUG] DOCLING_OUTPUT_DIR=./docling_output
[DEBUG] MODEL_NAME=ollama:granite3.1-dense:8b
[DEBUG] HOST=0.0.0.0, PORT=8080, DEBUG_MODE=True
[INFO] Docling output directory: ./docling_output
[INFO] Initializing TutorialGeneratorWorkflow...
[Workflow] Initializing (use_mocks=False, model=ollama:granite3.1-dense:8b)
[Workflow][WARNING] REPLICATE_API_TOKEN not set. Using mocks.
[SourceRetriever] Initialized with retry strategy.
[Parser] Initialized with output_dir=./docling_output
[Parser] HybridChunker initialized.
[Analyzer] Initializing ContentAnalyzerAgent (use_mocks=True, model_name='ollama:granite3.1-dense:8b')
[Analyzer] Initializing models for 'ollama:granite3.1-dense:8b'...
[Analyzer] Using mock models.
[Analyzer] Initialized _MockChatModel for ollama:granite3.1-dense:8b
[Analyzer] Initialized _MockVision for ollama:granite3.1-dense:8b
TutorialStructureAgent: using mock ChatModel
[MarkdownGenerationAgent] Initializing: Using mock ChatModel
[_MockChatModel] Initialized for ollama:granite3.1-dense:8b
[Workflow] All agents initialized.
[INFO] Workflow initialized.
[DEBUG] __main__ entry, argv=['src/main.py', 'https://www.adobe.com/support/products/enterprise/knowledgecenter/media/c4611_sample_explain.pdf']
[CLI] generating tutorial for: https://www.adobe.com/support/products/enterprise/knowledgecenter/media/c4611_sample_explain.pdf

[Workflow] Starting for source: https://www.adobe.com/support/products/enterprise/knowledgecenter/media/c4611_sample_explain.pdf

[Step 1] Retrieving source content...
[SourceRetriever] run() start for 'https://www.adobe.com/support/products/enterprise/knowledgecenter/media/c4611_sample_explain.pdf'
[SourceRetriever] Input is URL: https://www.adobe.com/support/products/enterprise/knowledgecenter/media/c4611_sample_explain.pdf
[SourceRetriever] Fetching URL...
[SourceRetriever] HTTP 200
[SourceRetriever] Content-Type: application/pdf
[SourceRetriever] Detected PDF via Content-Type.
[SourceRetriever] PDF saved to temporary file: /tmp/tmp4bm1xcis.pdf
[SourceRetriever] Registered /tmp/tmp4bm1xcis.pdf for cleanup on exit.
[SourceRetriever] Returning Document(format='pdf', content_type=<class 'str'>, source='https://www.adobe.com/support/products/enterprise/knowledgecenter/media/c4611_sample_explain.pdf')
[Timing] SourceRetrieverAgent.run: 0.07s
[Debug] raw_doc.metadata: {'format': 'pdf', 'source': 'https://www.adobe.com/support/products/enterprise/knowledgecenter/media/c4611_sample_explain.pdf'}
[Debug] raw_doc.page_content snippet: '/tmp/tmp4bm1xcis.pdf'

[Step 2] Parsing document...
[Step 2] Parsing document...
[Parser] run() start for source='https://www.adobe.com/support/products/enterprise/knowledgecenter/media/c4611_sample_explain.pdf' format='pdf'
[Parser][DEBUG] raw_doc.page_content (input path/content): '/tmp/tmp4bm1xcis.pdf'
[Parser] Creating DocumentConverter instance...
[Parser][DEBUG] Converter.convert signature: (source: Union[pathlib.Path, str, docling_core.types.io.DocumentStream], headers: Optional[Dict[str, str]] = None, raises_on_error: bool = True, max_num_pages: int = 9223372036854775807, max_file_size: int = 9223372036854775807, page_range: Annotated[Tuple[int, int], PlainValidator(func=<function _validate_page_range at 0x7f68020c7b00>, json_schema_input_type=Any)] = (1, 9223372036854775807)) -> docling.datamodel.document.ConversionResult
[Parser] Calling converter.convert(source='/tmp/tmp4bm1xcis.pdf') with no extra options...
[Parser][DEBUG] Conversion output type: <class 'docling.datamodel.document.ConversionResult'>, preview: ConversionResult(input=InputDocument(file=PurePosixPath('tmp4bm1xcis.pdf'), document_hash='2353deadc9fa87817413b239841a373fb51de8b74a75d3c8c863de735ca
[Parser][DEBUG] Extracted DoclingDocument type: <class 'docling_core.types.doc.document.DoclingDocument'>
[Parser] Chunking parsed document...
[Parser] Chunking complete: produced 7 chunks.
[Parser][DEBUG] First chunk type: <class 'docling_core.transforms.chunker.hierarchical_chunker.DocChunk'>, preview: DocChunk(text='Prepared by:, May 2001 = Accelio Present Applied Technology. Created and Tested Using
[Parser] Successfully created 7 LangChain documents.
[Timing] DocumentParserAgent.run: 9.21s
[Debug] Parsed blocks count: 7
[Debug] First block snippet: 'Prepared by:, May 2001 = Accelio Present Applied Technology. Created and Tested Using:, May 2001 = • Accelio Present Central 5.4 • Accelio Present Output Designer 5.4. Features Demonstrated:, May 2001'

[Step 3] Analyzing blocks...
[Analyzer] Starting analysis for 7 blocks...
[Analyzer] Block 1/7
[Analyzer] Sending block 1 text to ChatModel...
[Analyzer] Raw response block 1: {"role": "concept", "summary": "Mock summary: type='text' text='Prepared by:, May 2001 = Accelio..."}
[Analyzer] Parsed response block 1: Role='concept', Summary='Mock summary: type='text' text='Prepared by:, May ...'
[Analyzer] Block 2/7
[Analyzer] Sending block 2 text to ChatModel...
[Analyzer] Raw response block 2: {"role": "concept", "summary": "Mock summary: type='text' text='This sample consists of a simple..."}
[Analyzer] Parsed response block 2: Role='concept', Summary='Mock summary: type='text' text='This sample consis...'
[Analyzer] Block 3/7
[Analyzer] Sending block 3 text to ChatModel...
[Analyzer] Raw response block 3: {"role": "concept", "summary": "Mock summary: type='text' text='^reformat trunc ^symbolset WINLA..."}
[Analyzer] Parsed response block 3: Role='concept', Summary='Mock summary: type='text' text='^reformat trunc ^s...'
[Analyzer] Block 4/7
[Analyzer] Sending block 4 text to ChatModel...
[Analyzer] Raw response block 4: {"role": "concept", "summary": "Mock summary: type='text' text='ap_bookmark.IFD, Description = T..."}
[Analyzer] Parsed response block 4: Role='concept', Summary='Mock summary: type='text' text='ap_bookmark.IFD, D...'
[Analyzer] Block 5/7
[Analyzer] Sending block 5 text to ChatModel...
[Analyzer] Raw response block 5: {"role": "concept", "summary": "Mock summary: type='text' text='To deploy this sample in your en..."}
[Analyzer] Parsed response block 5: Role='concept', Summary='Mock summary: type='text' text='To deploy this sam...'
[Analyzer] Block 6/7
[Analyzer] Sending block 6 text to ChatModel...
[Analyzer] Raw response block 6: {"role": "concept", "summary": "Mock summary: type='text' text='Invoices, Use the command line p..."}
[Analyzer] Parsed response block 6: Role='concept', Summary='Mock summary: type='text' text='Invoices, Use the ...'
[Analyzer] Block 7/7
[Analyzer] Sending block 7 text to ChatModel...
[Analyzer] Raw response block 7: {"role": "concept", "summary": "Mock summary: type='text' text='- \u00b7 To run this sample, place ap..."}
[Analyzer] Parsed response block 7: Role='concept', Summary='Mock summary: type='text' text='- · To run this sa...'
[Analyzer] Completed analysis: 7 items.
[Timing] ContentAnalyzerAgent.run: 0.00s
[Debug] Insights count: 7
[Debug] First insight snippet: "Mock summary: type='text' text='Prepared by:, May 2001 = Accelio..."

[Step 4] Structuring outline...
[Timing] TutorialStructureAgent.run: 0.00s
[Debug] outline_doc.metadata: {'role': 'outline'}

[Step 5] Generating Markdown tutorial...
[MarkdownGenerationAgent] Run called. Mocks enabled: True
[MarkdownGenerationAgent] Formatted insights string (first 300 chars): - (concept) Mock summary: type='text' text='Prepared by:, May 2001 = Accelio...
- (concept) Mock summary: type='text' text='This sample consists of a simple...
- (concept) Mock summary: type='text' text='^reformat trunc ^symbolset WINLA...
- (concept) Mock summary: type='text' text='ap_bookmark.IFD,...
[MarkdownGenerationAgent] Combined user message content (first 400 chars): Outline:
```markdown
# Tutorial Outline

## Introduction
- Overview of the main topic based on identified concepts.

## Prerequisites
- List any prerequisites identified.

## Steps
1. Step 1 summary.
2. Step 2 summary.
3. Step 3 summary.

## Examples
- Example 1 description.
- Example 2 description.

## Conclusion
- Final thoughts and next steps.
```

---
Insights:
- (concept) Mock summary: type='...
[MarkdownGenerationAgent] Calling chat_model.create (model: ollama:granite3.1-dense:8b)
[_MockChatModel] Create called
[_MockChatModel][ERROR] Failed to parse input content: 'list' object has no attribute 'splitlines'
[_MockChatModel] Generated mock markdown (length: 287)
[MarkdownGenerationAgent] chat_model.create call completed.
[MarkdownGenerationAgent] Received markdown content (length: 286).
[Timing] MarkdownGenerationAgent.run: 0.00s
[Debug] draft_doc.metadata: {'role': 'tutorial_draft', 'status': 'generated'}

[Step 6] Reviewing & refining...
[Timing] ReviewerRefinerAgent.run: 0.00s
[Debug] final_doc.metadata: {'role': 'tutorial_refined', 'status': 'refined_mock'}
[Workflow] Tutorial refined successfully.

[Workflow] Completed successfully in 9.29s

--- Generated Markdown Tutorial ---

Mock Refinement: No input content found.

--- End of Tutorial ---

[Cleanup] Deleting 1 temporary files...
[Cleanup] Deleted: /tmp/tmp4bm1xcis.pdf
