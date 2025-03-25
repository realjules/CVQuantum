import re
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LaTeXParser:
    """
    Parser for LaTeX CV documents that extracts sections, content, and structure.
    Enables modification and customization of LaTeX documents based on job requirements.
    """
    
    def __init__(self):
        self.document_structure = {}
        self.preamble = ""
        self.sections = {}
        self.begin_document_index = -1
        self.end_document_index = -1
        self.raw_content = []
        
    def parse_file(self, file_path: str) -> bool:
        """
        Parse a LaTeX file and extract its structure
        
        Args:
            file_path: Path to the LaTeX file
            
        Returns:
            bool: True if parsing was successful, False otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                self.raw_content = file.readlines()
            
            self._identify_document_boundaries()
            self._extract_preamble()
            self._extract_sections()
            
            logger.info(f"Successfully parsed LaTeX file: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error parsing LaTeX file: {e}")
            return False
    
    def parse_content(self, latex_content: str) -> bool:
        """
        Parse LaTeX content from a string
        
        Args:
            latex_content: String containing LaTeX content
            
        Returns:
            bool: True if parsing was successful, False otherwise
        """
        try:
            self.raw_content = latex_content.splitlines(True)
            
            self._identify_document_boundaries()
            self._extract_preamble()
            self._extract_sections()
            
            logger.info("Successfully parsed LaTeX content from string")
            return True
            
        except Exception as e:
            logger.error(f"Error parsing LaTeX content: {e}")
            return False
    
    def _identify_document_boundaries(self) -> None:
        """Identify the begin and end document tags"""
        for i, line in enumerate(self.raw_content):
            if r"\begin{document}" in line:
                self.begin_document_index = i
            elif r"\end{document}" in line:
                self.end_document_index = i
                
        if self.begin_document_index == -1 or self.end_document_index == -1:
            raise ValueError("Could not find document boundaries (\\begin{document} and \\end{document})")
    
    def _extract_preamble(self) -> None:
        """Extract the preamble (content before \begin{document})"""
        if self.begin_document_index > 0:
            self.preamble = ''.join(self.raw_content[:self.begin_document_index])
    
    def _extract_sections(self) -> None:
        """Extract sections from the document body"""
        # Regular expression to match section commands
        section_pattern = re.compile(r"\\(section|subsection|subsubsection)\{([^}]+)\}")
        
        current_section = None
        section_content = []
        section_start_line = -1
        
        # Process the document body (between begin and end document)
        for i in range(self.begin_document_index + 1, self.end_document_index):
            line = self.raw_content[i]
            
            # Check if this line starts a new section
            match = section_pattern.search(line)
            if match:
                # If we were already processing a section, save it
                if current_section:
                    self.sections[current_section] = {
                        'content': ''.join(section_content),
                        'start_line': section_start_line,
                        'end_line': i - 1
                    }
                
                # Start new section
                current_section = match.group(2)  # Section name
                section_content = [line]
                section_start_line = i
            elif current_section:
                # Add line to current section
                section_content.append(line)
        
        # Don't forget to add the last section
        if current_section:
            self.sections[current_section] = {
                'content': ''.join(section_content),
                'start_line': section_start_line,
                'end_line': self.end_document_index - 1
            }
    
    def get_section(self, section_name: str) -> Optional[str]:
        """
        Get the content of a specific section
        
        Args:
            section_name: Name of the section to retrieve
            
        Returns:
            str or None: Content of the section if found, None otherwise
        """
        if section_name in self.sections:
            return self.sections[section_name]['content']
        return None
    
    def get_all_sections(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all extracted sections
        
        Returns:
            dict: Dictionary with section names as keys and section details as values
        """
        return self.sections
    
    def extract_skills(self) -> List[str]:
        """
        Extract skills mentioned in the document, typically from a skills section
        
        Returns:
            list: List of skills found in the document
        """
        skills = []
        skill_section_names = ["Skills", "Technical Skills", "Core Competencies"]
        
        for section_name in skill_section_names:
            section_content = self.get_section(section_name)
            if section_content:
                # Look for itemize environments
                items_pattern = re.compile(r"\\begin\{itemize\}(.*?)\\end\{itemize\}", re.DOTALL)
                items_match = items_pattern.search(section_content)
                
                if items_match:
                    items = items_match.group(1)
                    item_pattern = re.compile(r"\\item\s+(.*?)(?=\\item|\n\\end)", re.DOTALL)
                    for match in item_pattern.finditer(items):
                        skills.append(match.group(1).strip())
                
        return skills
    
    def extract_experience(self) -> List[Dict[str, Any]]:
        """
        Extract experience entries from the document
        
        Returns:
            list: List of dictionaries with experience details
        """
        experiences = []
        experience_section_names = ["Experience", "Work Experience", "Professional Experience"]
        
        for section_name in experience_section_names:
            section_content = self.get_section(section_name)
            if not section_content:
                continue
                
            # Pattern to match experience entries (assuming they use some environment)
            entry_pattern = re.compile(r"\\begin\{(.*?)\}(.*?)\\end\{\1\}", re.DOTALL)
            
            for match in entry_pattern.finditer(section_content):
                env_name = match.group(1)
                content = match.group(2)
                
                # Look for key information within this entry
                title_match = re.search(r"\\textbf\{(.*?)\}", content)
                company_match = re.search(r"\\textit\{(.*?)\}", content)
                date_match = re.search(r"\\hfill\{?(.*?)\}?(?=\\\\|$)", content)
                
                experience = {
                    "title": title_match.group(1) if title_match else "",
                    "company": company_match.group(1) if company_match else "",
                    "date": date_match.group(1) if date_match else "",
                    "content": content
                }
                
                experiences.append(experience)
                
        return experiences
    
    def modify_section(self, section_name: str, new_content: str) -> bool:
        """
        Modify the content of a specified section
        
        Args:
            section_name: Name of the section to modify
            new_content: New content for the section
            
        Returns:
            bool: True if modification was successful, False otherwise
        """
        if section_name not in self.sections:
            logger.error(f"Section '{section_name}' not found in the document")
            return False
            
        section = self.sections[section_name]
        start = section['start_line']
        end = section['end_line']
        
        # Replace the section content in raw_content
        self.raw_content[start:end+1] = new_content.splitlines(True)
        
        # Update the document structure
        self._identify_document_boundaries()
        self._extract_sections()
        
        return True
    
    def add_section(self, section_name: str, content: str, position: str = "end") -> bool:
        """
        Add a new section to the document
        
        Args:
            section_name: Name of the new section
            content: Content of the new section
            position: Where to add the section ("start", "end", or after a specific section)
            
        Returns:
            bool: True if addition was successful, False otherwise
        """
        section_cmd = f"\\section{{{section_name}}}\n"
        full_content = section_cmd + content
        
        try:
            # Insert at specified position
            if position == "start":
                insert_pos = self.begin_document_index + 1
            elif position == "end":
                insert_pos = self.end_document_index
            elif position in self.sections:
                insert_pos = self.sections[position]['end_line'] + 1
            else:
                logger.error(f"Invalid position: {position}")
                return False
                
            # Insert the new section
            new_lines = full_content.splitlines(True)
            self.raw_content[insert_pos:insert_pos] = new_lines
            
            # Update document structure
            self._identify_document_boundaries()
            self._extract_sections()
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding section: {e}")
            return False
    
    def reorder_sections(self, order: List[str]) -> bool:
        """
        Reorder sections based on provided list
        
        Args:
            order: List of section names in desired order
            
        Returns:
            bool: True if reordering was successful, False otherwise
        """
        try:
            # Check if all sections exist
            for section in order:
                if section not in self.sections:
                    logger.error(f"Section '{section}' not found in document")
                    return False
            
            # Create a new document body
            new_body = []
            for section in order:
                section_data = self.sections[section]
                content_lines = self.raw_content[section_data['start_line']:section_data['end_line']+1]
                new_body.extend(content_lines)
            
            # Replace document body
            self.raw_content[self.begin_document_index+1:self.end_document_index] = new_body
            
            # Update document structure
            self._identify_document_boundaries()
            self._extract_sections()
            
            return True
            
        except Exception as e:
            logger.error(f"Error reordering sections: {e}")
            return False
    
    def generate_latex(self) -> str:
        """
        Generate LaTeX content from the current document structure
        
        Returns:
            str: Complete LaTeX document content
        """
        return ''.join(self.raw_content)
    
    def save_to_file(self, file_path: str) -> bool:
        """
        Save the current document to a file
        
        Args:
            file_path: Path where the file should be saved
            
        Returns:
            bool: True if saving was successful, False otherwise
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(self.generate_latex())
            logger.info(f"Successfully saved LaTeX document to: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving LaTeX document: {e}")
            return False


# Helper functions for common LaTeX patterns
def extract_latex_command_content(text: str, command: str) -> List[str]:
    """
    Extract content from a LaTeX command like \\command{content}
    
    Args:
        text: Text to search in
        command: LaTeX command without backslash
    
    Returns:
        list: List of matched content
    """
    pattern = re.compile(fr"\\{command}\{{(.*?)\}}", re.DOTALL)
    return [match.group(1) for match in pattern.finditer(text)]

def extract_environment_content(text: str, env_name: str) -> List[str]:
    """
    Extract content from a LaTeX environment
    
    Args:
        text: Text to search in
        env_name: Environment name
    
    Returns:
        list: List of matched environment content
    """
    pattern = re.compile(fr"\\begin\{{{env_name}\}}(.*?)\\end\{{{env_name}\}}", re.DOTALL)
    return [match.group(1) for match in pattern.finditer(text)]