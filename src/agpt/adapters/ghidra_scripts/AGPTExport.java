// AGPT metadata exporter for Ghidra Headless. No decompilation or code modification.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class AGPTExport extends GhidraScript {
    private String quote(String value) {
        if (value == null) return "null";
        StringBuilder out = new StringBuilder("\"");
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (c == '\"') out.append("\\\"");
            else if (c == '\\') out.append("\\\\");
            else if (c == '\n') out.append("\\n");
            else if (c == '\r') out.append("\\r");
            else if (c == '\t') out.append("\\t");
            else if (c < 0x20) out.append(String.format("\\u%04x", (int)c));
            else out.append(c);
        }
        return out.append('\"').toString();
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) throw new IllegalArgumentException("Expected output JSON path and max function count");
        Path output = Path.of(args[0]);
        int maxFunctions = Integer.parseInt(args[1]);
        if (maxFunctions < 1 || maxFunctions > 100000) throw new IllegalArgumentException("Invalid function limit");

        StringBuilder json = new StringBuilder();
        json.append("{\n  \"schema_version\": \"1.0\",");
        json.append("\n  \"program\": {");
        json.append("\n    \"name\": ").append(quote(currentProgram.getName())).append(',');
        json.append("\n    \"executable_format\": ").append(quote(currentProgram.getExecutableFormat())).append(',');
        json.append("\n    \"language_id\": ").append(quote(currentProgram.getLanguageID().toString())).append(',');
        json.append("\n    \"compiler_spec_id\": ").append(quote(currentProgram.getCompilerSpec().getCompilerSpecID().toString())).append(',');
        json.append("\n    \"image_base\": ").append(quote(currentProgram.getImageBase().toString())).append(',');
        json.append("\n    \"min_address\": ").append(quote(currentProgram.getMinAddress().toString())).append(',');
        json.append("\n    \"max_address\": ").append(quote(currentProgram.getMaxAddress().toString()));
        json.append("\n  },");
        String[] externalNames = currentProgram.getExternalManager().getExternalLibraryNames();
        List<String> libraries = new ArrayList<String>();
        Collections.addAll(libraries, externalNames);
        Collections.sort(libraries);
        int libraryLimit = Math.min(libraries.size(), 4096);
        json.append("\n  \"external_libraries\": [");
        for (int i = 0; i < libraryLimit; i++) {
            if (i > 0) json.append(',');
            json.append(quote(libraries.get(i)));
        }
        json.append("],\n  \"external_libraries_truncated\": ").append(libraries.size() > libraryLimit).append(',');
        FunctionIterator iterator = currentProgram.getFunctionManager().getFunctions(true);
        List<String> functions = new ArrayList<String>();
        int seen = 0;
        while (iterator.hasNext() && seen < maxFunctions) {
            Function function = iterator.next();
            functions.add("{\"name\":" + quote(function.getName()) +
                ",\"entry_point\":" + quote(function.getEntryPoint().toString()) + "}");
            seen++;
            if (seen % 1000 == 0) monitor.checkCancelled();
        }
        boolean truncated = iterator.hasNext();
        json.append("\n  \"functions\": [");
        for (int i = 0; i < functions.size(); i++) {
            if (i > 0) json.append(',');
            json.append(functions.get(i));
        }
        json.append("],\n  \"functions_exported\": ").append(functions.size()).append(',');
        json.append("\n  \"functions_truncated\": ").append(truncated).append(',');
        json.append("\n  \"memory_block_count\": ").append(currentProgram.getMemory().getBlocks().length);
        json.append("\n}\n");
        Files.createDirectories(output.toAbsolutePath().getParent());
        Files.write(output, json.toString().getBytes(StandardCharsets.UTF_8));
        println("AGPT metadata exported to " + output.toAbsolutePath());
    }
}