import sys
import io
import logging
import traceback
from typing import Dict, Any

log = logging.getLogger("ferramenteiro.service")

class FerramenteiroService:
    def execute_code(self, code: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executes Python code in a restricted (but not fully jailed for MVP) environment.
        Returns stdout, stderr and updated context.
        """
        if context is None:
            context = {}

        # Capture output
        stdout = io.StringIO()
        stderr = io.StringIO()
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stdout
        sys.stderr = stderr
        
        success = True
        error_msg = ""
        
        try:
            # Simple restricted globals
            exec_globals = {
                "__builtins__": __builtins__,
                "pd": None, # Could auto-import if available
                "np": None,
                "plt": None,
            }
            # Add context to globals
            exec_globals.update(context)
            
            exec(code, exec_globals)
            
            # Extract updated variables (excluding builtins and modules)
            new_context = {k: v for k, v in exec_globals.items() 
                           if not k.startswith("__") and not hasattr(v, "__module__")}
            
        except Exception:
            success = False
            error_msg = traceback.format_exc()
            log.error("Code execution failed:\n%s", error_msg)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        return {
            "success": success,
            "stdout": stdout.getvalue(),
            "stderr": stderr.getvalue() or error_msg,
            "context": new_context if success else context
        }

ferramenteiro_service = FerramenteiroService()
