# Progress note

1. 23052026 - Finally fix the reading and force docling to extract all text. Some rough edges exist but I think it can be removed using manual programming. For the next task I think I should have rolling document reader since there is no way I could feed all of it to deepseek. I also should integrate the graph database so any reads can be safely stored.

2. 27052026 - The reading and saving now merged to one toolbox due to separating it make the parsing and read file as a message to LLM server which would overwhelm thus get rejected. Next I want to implement the rolling document. This is to test the long running yet simple task for deepseek. It seems like using **FalkorDB** is the way. We should share the volume to keep it persistent.

3. 29052026 - Rolling reads for untangling OCR parse is successful. There is some flaw here and there but it is more manageable compared to read the whole OCR. Rolling reads can be used to reads fund sheet, establish a relationship and store it.

4. 29052026 - Installing FalkorDB. This would be the main storage for the graph. Ideally the text would be read in rolling sequence yet chunked via paragraph. Semantic tool would parse its entities in cypher query. FalkorDB tooling would update the the graph and enrich the graph until all document is consumed. **I still need to find a way to minimise the messaging to deepseek since rolling document would keep appending. If I only submit last few arrays, then it would missing the system context.**

5. 30052026 - Apparently Deepseek can do multiple call to reduce message numbers. I need to somehow utilize more.

6. 30052026 - I'm thinking about orchestrator dispatching task so it wont clutter the main message line. We need to create sub orcehstrator; a class where it still take some input, feed it to prompt and has its own tool alocation. The orchestrator then collec sub orchestrator tooling then just call it. For example, in the rolling relationship extraction, the main orchestrator would chunk the file into tens of manageable bytes. It should pass the file path and the chunks it reads to the sub orchestrator. Suborchestrator have their own messaging line and would end once it establish a relationship and store in FalkorDB. Furthermore, it can be parallelized and the main orchestrator can wait the result.