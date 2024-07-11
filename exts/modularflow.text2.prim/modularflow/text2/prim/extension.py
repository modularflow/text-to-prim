import omni.ext
import omni.ui as ui
import omni.usd
from pxr import Gf, UsdGeom, Sdf
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
     - prim: string - the name of the prim to spawn: cube, sphere, cylinder, cone, capsule

2. change_color
   Description: Changes the color of an object in the Omniverse scene
   Arguments:
     - object_name: string - The name of the object to change color
     - color: string - The new color for the object (e.g., "red", "blue", "#FF0000")

3. move_prim
   Description: Moves the selected prim(s) by a specified amount
   Arguments:
     - x(left - and right +): float - The amount to move in the X direction (left/right)
     - y(down - and up +): float - The amount to move in the Y direction (up/down)
     - z(backward - and forward +): float - The amount to move in the Z direction (backward/forward)

4. rotate_prim
   Description: Rotates the selected prim(s) by a specified amount (in degrees)
   Arguments:
     - x: float - The amount to rotate around the X axis
     - y: float - The amount to rotate around the Y axis
     - z: float - The amount to rotate around the Z axis

5. select_parent
   Description: Selects the parent(s) of the currently selected prim(s)
   Arguments: None

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
        self._response_label.text = str(llm_response)  # Update UI with response
        
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
            attributes = {'size': size}
        elif prim.lower() == "sphere":
            attributes = {'radius': half_size}
        elif prim.lower() in ["cylinder", "cone", "capsule"]:
            attributes = {'height': size, 'radius': half_size}
        else:
            print(f"Unknown prim type: {prim}")
            return

        prim_path = f"/World/{prim.capitalize()}_{len(omni.usd.get_context().get_stage().GetPrimAtPath('/World').GetChildren()) + 1}"
        
        omni.kit.commands.execute('CreatePrimWithDefaultXform',
            prim_type=prim.capitalize(),
            prim_path=prim_path,
            attributes=attributes)
        
        stage = omni.usd.get_context().get_stage()
        prim_obj = stage.GetPrimAtPath(prim_path)
        xform = UsdGeom.Xformable(prim_obj)
        
        if prim.lower() in ["cylinder", "cone", "capsule"]:
            xform.AddTranslateOp().Set(Gf.Vec3d(0, half_size, 0))
        
        print(f"Spawned a {prim} at {prim_path}")

    def change_color(self, object_name="", color=""):
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(f"/World/{object_name}")
        if not prim:
            print(f"Object '{object_name}' not found")
            return
        
        color_map = {
            "red": (1, 0, 0),
            "green": (0, 1, 0),
            "blue": (0, 0, 1),
            # Add more colors as needed
        }
        rgb = color_map.get(color.lower(), (1, 1, 1))  # Default to white if color not recognized
        
        material_path = Sdf.Path(f"{prim.GetPath()}/Material")
        omni.kit.commands.execute('CreateMdlMaterialPrim',
            mtl_url='omniverse://localhost/NVIDIA/Materials/Base/Matte.mdl',
            mtl_name='Matte',
            mtl_path=str(material_path)
        )
        omni.kit.commands.execute('BindMaterial',
            prim_path=str(prim.GetPath()),
            material_path=str(material_path)
        )
        omni.kit.commands.execute('ChangeProperty',
            prop_path=f'{material_path}.inputs:diffuse_color_constant',
            value=Gf.Vec3f(*rgb),
            prev=None
        )
        
        print(f"Changed color of '{object_name}' to {color}")

    def move_prim(self, x: float, y: float, z: float):
        self._transform_prim(Gf.Vec3d(x, y, z), is_move=True)

    def rotate_prim(self, x: float, y: float, z: float):
        self._transform_prim(Gf.Vec3d(x, y, z), is_move=False)

    def _transform_prim(self, transform_value, is_move):
        stage = omni.usd.get_context().get_stage()
        selection = omni.usd.get_context().get_selection()
        paths = selection.get_selected_prim_paths()
        
        if not paths:
            print("No prim selected")
            return

        for path in paths:
            prim = stage.GetPrimAtPath(path)
            if not prim:
                continue

            xformable = UsdGeom.Xformable(prim)
            if not xformable:
                continue

            xform_ops = xformable.GetOrderedXformOps()
            op_type = UsdGeom.XformOp.TypeTranslate if is_move else UsdGeom.XformOp.TypeRotateXYZ
            transform_op = next((op for op in xform_ops if op.GetOpType() == op_type), None)
            
            if not transform_op:
                transform_op = xformable.AddTranslateOp() if is_move else xformable.AddRotateXYZOp()
            
            current_value = transform_op.Get()
            if current_value is None:
                current_value = Gf.Vec3d(0, 0, 0)
            
            new_value = current_value + transform_value
            
            transform_op.Set(new_value)

        action = "Moved" if is_move else "Rotated"
        print(f"{action} selected prims by ({transform_value[0]}, {transform_value[1]}, {transform_value[2]})")

    def select_parent(self):
        stage = omni.usd.get_context().get_stage()
        selection = omni.usd.get_context().get_selection()
        paths = selection.get_selected_prim_paths()

        if not paths:
            print("No objects selected")
            return

        new_selection = []
        for path in paths:
            prim = stage.GetPrimAtPath(path)
            if not prim:
                continue

            parent = prim.GetParent()
            if parent and not parent.IsPseudoRoot():
                new_selection.append(str(parent.GetPath()))
            else:
                new_selection.append(str(path))

        if new_selection:
            selection.set_selected_prim_paths(new_selection, False)
            print(f"Selected parent(s): {', '.join(new_selection)}")
        else:
            print("No valid parents found")