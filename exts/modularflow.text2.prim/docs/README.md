# [modularflow.text2.prim]

This extension uses langchain to connect an LLM for function calling.  
It's currently stood up to use ollama with llama3.  

For installation instructions for Ollama, please visit: https://github.com/ollama/ollama  

I'm unsure if you have to pip install langchain and langchain_community  
prior to using or if it will install it as a dependency from the toml.  
In case you need to install the dependency yourself you will need  
to open extensions > pipapiextension and then open extensions > script editor  within omniverse and paste the following:  

import omni.kit.pipapi  

omni.kit.pipapi.install(  
    package="langchain",  
    version="0.2.7,  
    module="langchain",   
    ignore_import_check=False,  
    ignore_cache=False,  
    use_online_index=True,  
    surpress_output=False,  
    extra_args=[]  
)
omni.kit.pipapi.install(  
    package="langchain_community",  
    version="0.2.7,  
    module="langchain_community",  
    ignore_import_check=False,  
    ignore_cache=False,  
    use_online_index=True,  
        surpress_output=False,  
    extra_args=[]  
)  

import langchain  
import langchain_community  


