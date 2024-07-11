import omni.ext
import omni.ui as ui
from pxr import Gf, Sdf, UsdGeom
import omni.kit.commands
from langchain_community.llms import Ollama
from langchain.schema.runnable import RunnableSequence
from langchain.prompts import PromptTemplate
import json
import re
FUNCTION_DESCRIPTIONS = """
Available functions:

1. spawn
Description: Creates a prim in the Omniverse scene
Arguments:
    - prim: string - the name of the prim to spawn: Cube, Sphere, Cylinder, Cone, Capsule

Response format:
{
"function": "function_name",
"arguments": {
    "arg1": value1,
    "arg2": value2
}
}
"""

class LLMOmniverseExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("[text2prim] text2prim extension startup")
        self._window = ui.Window("text2prim", width=300, height=300)

        # Initialize LangChain components
        self.llm = Ollama(base_url="http://localhost:11434", model="llama3")
        self.prompt = PromptTemplate(
            input_variables=["function_descriptions", "input"],
            template="""You are an AI assistant that helps control an Omniverse scene. 
Based on the user's input, decide which function to call and with what arguments.

{function_descriptions}

User input: {input}

Your response:"""
        )
        self.chain = RunnableSequence(
            self.prompt | self.llm
        )
        
        with self._window.frame:
            with ui.VStack():
                ui.Label("text2prim Extension")
                self._text_field = ui.StringField()
                ui.Button("Send to LLM", clicked_fn=self._on_send_to_llm)
                self._response_label = ui.Label("Response will appear here")


    def on_shutdown(self):
        print("[text2prim] text2prim extension shutdown")

    def _on_send_to_llm(self):
        user_input = self._text_field.model.get_value_as_string()
        llm_response = self._send_to_llm(user_input)
        self._process_llm_response(llm_response)

    def _send_to_llm(self, user_input):
        response = self.chain.invoke({
            "function_descriptions": FUNCTION_DESCRIPTIONS,
            "input": user_input
        })
        print(f"Raw LLM response: {response}")  # Debug print
        return response

    def _process_llm_response(self, llm_response):
        print(f"Processing LLM response: {llm_response}")  # Debug print
        self._response_label.text = str(llm_response)
        

        try:
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed_response = json.loads(json_str)
            else:
                raise ValueError("No JSON object found in the response")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing LLM response: {e}")
            return

        if "function" in parsed_response:
            function_name = parsed_response["function"]
            function_args = parsed_response.get("arguments", {})
            
            if hasattr(self, function_name):
                func = getattr(self, function_name)
                try:
                    func(**function_args)
                except TypeError as e:
                    print(f"Error calling function {function_name}: {e}")
            else:
                print(f"Function {function_name} not found")
        else:
            print("LLM response does not contain a function call")

    def spawn(self, prim):
        size = 100.0
        half_size = size / 2

        if prim.lower() == "cube":
            attributes = {
                'size': size
            }
        elif prim.lower() == "sphere":
            attributes = {
                'radius': half_size
            }
        elif prim.lower() in ["cylinder", "cone", "capsule"]:
            attributes = {
                'height': size,
                'radius': half_size
            }
        else:
            print(f"Unknown prim type: {prim}")
            return

        prim_path = f"/World/{prim.capitalize()}_{len(omni.usd.get_context().get_stage().GetPrimAtPath('/World').GetChildren()) + 1}"
        
        omni.kit.commands.execute('CreatePrimWithDefaultXform',
            prim_type=prim.capitalize(),
            prim_path=prim_path,
            attributes=attributes)
        
        # Adjust the transform to center the prim
        stage = omni.usd.get_context().get_stage()
        prim_obj = stage.GetPrimAtPath(prim_path)
        xform = UsdGeom.Xformable(prim_obj)
        
        if prim.lower() in ["cylinder", "cone", "capsule"]:
            xform.AddTranslateOp().Set(Gf.Vec3d(0, half_size, 0))
        
        print(f"Spawned a {prim} at {prim_path}")

