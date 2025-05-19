from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.utils.common import CodeParser

class FlutterDeveloper(Role):
    name = "Senior Flutter Developer"
    profile = "Expert in Flutter, Dart, Clean Architecture, and State Management"
    goal = "Generate a production-ready Flutter app with best practices"
    
    def _act(self, msg: Message) -> Message:
        prompt = f"""
        You are a senior Flutter developer. Follow these instructions strictly:
        
        1. **Project Structure**: Use Clean Architecture (data/domain/presentation layers).
        2. **State Management**: Use Riverpod or Bloc.
        3. **Required Files**:
           - main.dart (MaterialApp setup)
           - presentation/screens/ (HomeScreen, CartScreen, etc.)
           - presentation/widgets/ (reusable components)
           - data/repositories/ (API and local data sources)
           - domain/models/ (data classes)
           - pubspec.yaml (with necessary packages: http, riverpod, etc.)
        4. **Code Quality**: Add comments, null safety, and error handling.
        
        Product Spec:
        {msg.content}
        
        Output the full project structure with code for each file.
        """
        
        rsp = self.llm(prompt)
        code = CodeParser.parse_code(rsp)  # يفترض أن CodeParser يحول النص إلى ملفات
        return Message(content=code)