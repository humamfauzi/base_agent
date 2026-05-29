# Progress note

1. 23052026 - Finally fix the reading and force docling to extract all text. Some rough edges exist but I think it can be removed using manual programming. For the next task I think I should have rolling document reader since there is no way I could feed all of it to deepseek. I also should integrate the graph database so any reads can be safely stored.

2. 27052026 - The reading and saving now merged to one toolbox due to separating it make the parsing and read file as a message to LLM server which would overwhelm thus get rejected. Next I want to implement the rolling document. This is to test the long running yet simple task for deepseek. It seems like using **FalkorDB** is the way. We should share the volume to keep it persistent.

3. 29052026 - Rolling reads for untangling OCR parse is successful. There is some flaw here and there but it is more manageable compared to read the whole OCR. Rolling reads can be used to reads fund sheet, establish a relationship and store it.