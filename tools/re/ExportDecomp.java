// Decompiles every function in the program and writes the C pseudocode to the file given as the first script argument.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import java.io.*;

public class ExportDecomp extends GhidraScript {
    @Override
    public void run() throws Exception {
        String out = getScriptArgs()[0];
        DecompInterface d = new DecompInterface();
        d.toggleCCode(true);
        d.openProgram(currentProgram);
        int n = 0, fail = 0;
        try (PrintWriter w = new PrintWriter(new OutputStreamWriter(new FileOutputStream(out), "UTF-8"))) {
            for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
                if (f.isThunk() || f.isExternal()) continue;
                DecompileResults r = d.decompileFunction(f, 120, monitor);
                w.println("// ==== " + f.getName(true) + " @ " + f.getEntryPoint());
                if (r != null && r.decompileCompleted()) {
                    w.println(r.getDecompiledFunction().getC());
                } else {
                    fail++;
                    w.println("// decompile failed: " + (r == null ? "null" : r.getErrorMessage()));
                }
                n++;
            }
        }
        println("Decompiled " + n + " functions, " + fail + " failed");
    }
}
