#compose.yaml
We can think of removing compose.yaml if docker is not used
but is it the only place where the postgresql database is defined? what if we are not using docker where is the datbase setting?

#pyproject.toml  
want to understand if uv can be replaced by plain simple pip install and requirements.txt
want to fully understadn how does the cli part work, what is this  [project.scripts] section and how does the code of the cli and the cli interface really work

#config/engines.json, llm.json, system.json
We need to well document it, remember what we have and make use of it, think of any other hardcoded logic elsewhere int he code that coudl be placed here
Some ideas are e.g. default data path, default output path

#/config/loader.py
review langfuse and app variables also check if playbooks_seed_path should be deeclared here or elsewhere?

#papertrail/playbooks
papertrail/playbooks/models.py , papertrail/playbooks/merger.py , papertrail/playbooks/loader.py    
These (along with other related files) need a complete review and change as they are too hacky and complicated.
A few (soft) decisions
* For now the playbooks remain file based (but some format e.g. .json) but they can be datbase inserted (and still remain compatible as they shoudl be stored as json in db)
* The file based approach should not be of any restrictive nature as they can be thought of coming from a databsae
* The validation logic doesnt need to be very strict (it doesnt hurt though) 
* We need to make the base models strong and strict / robust so any child playbook extending it automatically is validated
* This playbook creation is really not the functionalty of the project, instead it is hand created by the team, so the only requirement really is that we should have no patch work, instead we use the base models, create the playbooks (properly) and just use it
* Strong base, samples for developers to follow should be good enough
* Validation step can be a failsafe if a file is corrupt, so the playbook does not run.
* System creates well documented base models and some samples (e.g. indian check), the developers will create the actual playbook by inheriting the base models (and using the validator tools). This also esnures that even if the playbook is coming from a file or database or typed, it still just works
** Clealry playbook has many moving parts (i am not being exhaustiev) but
we need abstract things properly e.g. engine config should be at system level, metaconfig, calssification, schema, validaiton, crossvalidation, rules, post process, etc should all have some base (default) and child (valid extensions). We need to be careful e..g Engines cannot be configured at the child levle, they can only be selcted. we can also think of abstraction using more classes. e.g. class for each of these sections (if appropirate)

Batch 2: papertrail/orchestration/*.

#papertrail/orchestration/graph.py
The nodes e.g. pass_a, pass_b etc arent they fixed (and thus limiting?)
Also, it seems the entire graph concept too shoudl be tightly coupled with the playbook. Is there a better way of doing this? We need to do some more reaerch on this direction. 
In the current impolmetnation the issues i notice are
* failrue not being handled (identified by you)
* it seems everthing is fixed in the graph.py and not really configuration (the whole issue)
* the steps too are defined (hence fixed not scalable or extensible)
The desired way should be (not exhaustive)
* Flexible
* Being able to read everything from the configs - playbook (bsae->child)
* Orchestrate the entire execution. The orchestratino layer should sit above so it can handle everything even if things go south
* Orchestration engline can also decide to skip execution (or decide accordingly) depending upon file health, config health, tool call helath, misconfigs etc

#papertrail/orchestration/
papertrail/orchestration/nodes.py
Most issues as the overall orchestration issues (i.e. mentioned in graph.py)
Additionalalyy this code is mostly stubs

papertrail/orchestration/routing.py, papertrail/orchestration/runner.py
same issues
but this is mostly ok for a fixed logic

==========

Batch 3

#papertrail/passes/* 
I think we need to rethink this. The primary qustion is whether this pre-processing is global/ssytem level or is it playbook level.
It is getting executed at system level but the settinsg are stored in playbook.
We need to resolve this. ì am more inclined towards moving this to the playbook itself as the first step. so the configuration will move into the playbook (base and child) and the execution should be managed by orchestration (graph/node) based on the configs
So effectively we are looking at moving this into playbook and orchestration (unless we have very very strong reasons not to)


## papertrail/llm/*   
This is tiny right now but functional. We need to work on 
the unimplemented calls (and see whther it is being used or will be used) e.g. call_raw
We need to implement openroute (as this is the real credit have) 
router needs to be implemented
lets decide whether fallback is really needed if not we can skip it

======================================

# papertrail/cli/*                                                                                                                                                                        
This is mostly Ok., We need to slowly work on all the mocks/stubs
one thing is that cli alwasy needs to be extended (and sycned) with all the funcionalty                                                                                                                                     We are first focussing on develping / orchestrating / testing the entire applicaiton using cli whcich will later be extend with (will maintain cli) fastAPI and then UI/UX

papertrail/playbooks/*                                                                                                                                                                  
Discussed before, we need to really rethink the fundamental loader/merger/inhetritence/schema validation logic and how it all fits with the orchestration
                                                                                                                                                                                            
 papertrail/config/* + config/*.json                                                                                                                                                     
Discussed before llm.json, engines.json, system.json are the main runtime config files.
Prompt templates are all present and align with the docs. But - There’s a mismatch between docs and current runtime in a few playbook/config shapes, especially preupload and validation structure. some techiniques are discused earlier, we need to brainshotrm further

# playbooks_seed/*                                                                                                                                                                        
We may need to redo this comletey in milestone 2 and beyond. Even right now we are not using it as we are using real PDF files for check and we cant really 
cretae seed data for each test, If our milestone 1 is ready with Core+Playbook then we dont need this anymore and infact we can think of smaller set of real data as seed. So lets not rely on creating seeds. instead we create the actual data (Core + data + playbook)

# tests/*                                                                                                                                                                                 
These are very outdated, I think after the fundamental changes we aer talking about we need to completely redo these. So we can remove this completey for now.

# scripts/*                                                                                                                                                                               
Lets remove this completey we are no more creaging these and we are using real data                                                                                                                                     

# Docs/specs                                                                                                                                                                              
We just continue to create new docs and maintain the detials of older ones. we may need to remoev/archive ones that are outdated compeltey or were temporary                                                                                                                                                                                             

 Biggest current gaps                                                                                                                                                                        
                                                                                                                                                                                             
 1. Persistence not wired into the runner                                                                                                                                                    
 2. LLM client still stubbed                                                                                                                                                                 
 3. Engine dispatcher still stubbed                                                                                                                                                          
 4. Validation and decision engines missing                                                                                                                                                  
 5. API package missing                                                                                                                                                                      
 6. HITL resume/cancel missing                                                                                                                                                               
 7. Several schema shapes differ between docs, seeds, and code                                                                                                                               
                                                                                                                                                                                             
 Bottom line                                                                                                                                                                                 
                                                                                                                                                                                             
 The repo is a solid foundation scaffold, not yet a production pipeline.                                                                                                                     
                                                                                                                                                                                             
 If you want, next I can do one of these:                                                                                                                                                    
 - Batch 3: papertrail/api/* + papertrail/validation/* + papertrail/decision/* + papertrail/tools/*                                                                                          
 - or I can switch to a single end-to-end gap map: “what’s implemented vs what’s still missing” across the whole repo.     ### papertrail/cli/*                                                                                                                                                                        
                                                                                                                                                                                             
 - CLI command tree is in place.                                                                                                                                                             
 - run, playbook, runs, hitl, db, eval all exist.                                                                                                                                            
 - Most commands are still mock/stub behavior.                                                                                                                                               
 - run is the only path that actually kicks off the pipeline.                                                                                                                                
 - formatters.py is simple and works for the current stub state.                                                                                                                             
                                                                                                                                                                                             
 ### papertrail/playbooks/*                                                                                                                                                                  
                                                                                                                                                                                             
 - Already covered previously, but I re-checked the current code shape:                                                                                                                      
     - loader/merger models are present                                                                                                                                                      
     - _base inheritance is the intended design                                                                                                                                              
     - current code and docs still have some schema-shape drift to resolve                                                                                                                   
                                                                                                                                                                                             
 ### papertrail/config/* + config/*.json                                                                                                                                                     
                                                                                                                                                                                             
 - llm.json, engines.json, system.json are the main runtime config files.                                                                                                                    
 - Prompt templates are all present and align with the docs.                                                                                                                                 
 - There’s a mismatch between docs and current runtime in a few playbook/config shapes, especially preupload and validation structure.                                                       
                                                                                                                                                                                             
 ### playbooks_seed/*                                                                                                                                                                        
                                                                                                                                                                                             
 - _base and indian_cheque seed sets are present.                                                                                                                                            
 - They mirror the current stub architecture:                                                                                                                                                
     - base engine defaults                                                                                                                                                                  
     - cheque-specific vision + preupload overrides                                                                                                                                          
     - basic classify/schema/validate/rules/postprocess sections                                                                                                                             
 - These seeds are enough for bootstrapping, but not yet enough for a full generic engine.                                                                                                   
                                                                                                                                                                                             
 ### tests/*                                                                                                                                                                                 
                                                                                                                                                                                             
 - Only a couple of real unit tests exist:                                                                                                                                                   
     - formatters                                                                                                                                                                            
     - routing                                                                                                                                                                               
 - Fixtures are helpful and match the sample docs.                                                                                                                                           
 - tests/integration, tests/evaluation are basically empty markers right now.                                                                                                                
                                                                                                                                                                                             
 ### scripts/*                                                                                                                                                                               
                                                                                                                                                                                             
 - generate_sample_inputs.py is useful and straightforward.                                                                                                                                  
 - It creates lightweight text fixtures, not real OCR/PDF corpora.                                                                                                                           
                                                                                                                                                                                             
 ### Docs/specs                                                                                                                                                                              
                                                                                                                                                                                             
 - I checked the architecture docs and they’re much more ambitious than the live code.                                                                                                       
 - The docs describe the target system well, but the repository is still mostly scaffolding + a few working utilities.                                                                       
                                           \
Other major gaps found                                                                                                                                                                                              
 1. Persistence not wired into the runner                                                                                                                                                    
 2. LLM client still stubbed                                                                                                                                                                 
 3. Engine dispatcher still stubbed                                                                                                                                                          
 4. Validation and decision engines missing                                                                                                                                                  
 5. API package missing                                                                                                                                                                      
 6. HITL resume/cancel missing                                                                                                                                                               
 7. Several schema shapes differ between docs, seeds, and code