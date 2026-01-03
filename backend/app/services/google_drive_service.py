import google.auth
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GoogleDriveService:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.service = self._get_drive_service()
        self.docs_service = self._get_docs_service()
        
    def _get_drive_service(self):
        """Initialize Google Drive service with default credentials"""
        try:
            credentials, _ = google.auth.default(
                scopes=['https://www.googleapis.com/auth/drive']
            )
            return build('drive', 'v3', credentials=credentials)
        except Exception as e:
            print(f"Error initializing Drive service: {e}")
            return None
    
    def _get_docs_service(self):
        """Initialize Google Docs service"""
        try:
            credentials, _ = google.auth.default(
                scopes=['https://www.googleapis.com/auth/documents']
            )
            return build('docs', 'v1', credentials=credentials)
        except Exception as e:
            print(f"Error initializing Docs service: {e}")
            return None
    
    def copy_template(self, template_id: str, new_title: str, folder_id: str = None):
        """Copy a Google Doc template and return the new document ID"""
        try:
            body = {'name': new_title}
            
            drive_response = self.service.files().copy(
                fileId=template_id,
                body=body
            ).execute()
            
            new_doc_id = drive_response.get('id')
            
            if folder_id:
                file = self.service.files().get(
                    fileId=new_doc_id,
                    fields='parents'
                ).execute()
                
                previous_parents = ",".join(file.get('parents', []))
                
                self.service.files().update(
                    fileId=new_doc_id,
                    addParents=folder_id,
                    removeParents=previous_parents,
                    fields='id, parents'
                ).execute()
            
            return new_doc_id
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None
    
    def fill_npc_template(self, doc_id: str, npc_data: dict):
        """Fill the NPC template with data"""
        try:
            replacements = {
                '{{NPC_NAME}}': npc_data.get('name', ''),
                '{{RACE}}': npc_data.get('race', ''),
                '{{CLASS}}': npc_data.get('class', ''),
                '{{ALIGNMENT}}': npc_data.get('alignment', ''),
                '{{LEVEL}}': npc_data.get('level', ''),
                '{{WORLD_PLACEMENT}}': npc_data.get('world_placement', ''),
                '{{PHYSICAL_DESCRIPTION}}': npc_data.get('physical_description', ''),
                '{{VOICE_SUGGESTIONS}}': npc_data.get('voice_suggestions', ''),
                '{{PERSONALITY_TRAITS}}': npc_data.get('personality_traits', ''),
                '{{BACKGROUND}}': npc_data.get('background', ''),
                '{{STR}}': npc_data.get('str', ''),
                '{{DEX}}': npc_data.get('dex', ''),
                '{{CON}}': npc_data.get('con', ''),
                '{{INT}}': npc_data.get('int', ''),
                '{{WIS}}': npc_data.get('wis', ''),
                '{{CHA}}': npc_data.get('cha', ''),
                '{{SAVING_THROWS}}': npc_data.get('saving_throws', ''),
                '{{SKILLS}}': npc_data.get('skills', ''),
                '{{SENSES}}': npc_data.get('senses', ''),
                '{{LANGUAGES}}': npc_data.get('languages', ''),
                '{{ABILITIES}}': npc_data.get('abilities', ''),
                '{{ACTIONS}}': npc_data.get('actions', ''),
            }
            
            requests = []
            for placeholder, value in replacements.items():
                requests.append({
                    'replaceAllText': {
                        'containsText': {
                            'text': placeholder,
                            'matchCase': True
                        },
                        'replaceText': str(value)
                    }
                })
            
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            
            return True
            
        except HttpError as error:
            print(f"An error occurred filling template: {error}")
            return False
    
    def get_document_url(self, doc_id: str):
        """Get the URL for a Google Doc"""
        return f"https://docs.google.com/document/d/{doc_id}/edit"
