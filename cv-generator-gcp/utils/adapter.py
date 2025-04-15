import logging
from typing import Dict, Any, List, Optional

class HireableCVAdapter:
    """
    Adapter utility for converting between CV Parser data format and CV Generator data format.
    """
    
    @staticmethod
    def parser_to_generator(parser_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert CV Parser data format to CV Generator format.
        
        Args:
            parser_data (Dict[str, Any]): The data from CV Parser service.
            
        Returns:
            Dict[str, Any]: Data in CV Generator format.
        """
        if not parser_data or not isinstance(parser_data, dict):
            return {}
            
        # Create base structure for CV Generator
        result = {
            "data": {
                # Map personal information
                "firstName": parser_data.get("contact_info", {}).get("first_name", ""),
                "surname": parser_data.get("contact_info", {}).get("last_name", ""),
                "email": parser_data.get("contact_info", {}).get("email"),
                "phone": parser_data.get("contact_info", {}).get("phone"),
                "address": parser_data.get("contact_info", {}).get("location"),
                "profileStatement": parser_data.get("personal_statement", ""),
            }
        }
        
        # Map linkedin and website from links
        if "links" in parser_data and isinstance(parser_data["links"], list):
            for link in parser_data["links"]:
                if isinstance(link, str):
                    if "linkedin" in link.lower():
                        result["data"]["linkedin"] = link
                    elif any(domain in link.lower() for domain in ["github", "gitlab"]):
                        result["data"]["website"] = link
        
        # Map skills
        if "skills" in parser_data and isinstance(parser_data["skills"], list):
            result["data"]["skills"] = parser_data["skills"]
        
        # Map experience items
        if "experience" in parser_data and isinstance(parser_data["experience"], list):
            result["data"]["experience"] = [
                {
                    "role": exp.get("title", ""),
                    "company": exp.get("company", ""),
                    "startDate": exp.get("start_date", ""),
                    "endDate": exp.get("end_date", ""),
                    "current": exp.get("is_current", False),
                    "description": exp.get("description", "")
                }
                for exp in parser_data["experience"]
            ]
            
        # Map education items
        if "education" in parser_data and isinstance(parser_data["education"], list):
            result["data"]["education"] = [
                {
                    "institution": edu.get("institution", ""),
                    "degree": edu.get("degree", ""),
                    "startDate": edu.get("start_date", ""),
                    "endDate": edu.get("end_date", ""),
                    "grade": edu.get("grade", "")
                }
                for edu in parser_data["education"]
            ]
        
        # Map certifications
        if "certifications" in parser_data and isinstance(parser_data["certifications"], list):
            result["data"]["certifications"] = [
                {
                    "name": cert.get("name", ""),
                    "issuer": cert.get("issuer", ""),
                    "date": cert.get("date", ""),
                    "description": cert.get("description", "")
                }
                for cert in parser_data["certifications"]
            ]
        
        # Map languages
        if "languages" in parser_data and isinstance(parser_data["languages"], list):
            result["data"]["languages"] = [
                {
                    "language": lang.get("language", ""),
                    "proficiency": lang.get("proficiency", "")
                }
                for lang in parser_data["languages"]
            ]
            
        # Map achievements
        if "achievements" in parser_data and isinstance(parser_data["achievements"], list):
            result["data"]["achievements"] = [
                {
                    "title": ach.get("title", ""),
                    "description": ach.get("description", ""),
                    "date": ach.get("date", "")
                }
                for ach in parser_data["achievements"]
            ]
            
        return result
    
    @staticmethod
    def generator_to_parser(generator_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert CV Generator data format to CV Parser format.
        
        Args:
            generator_data (Dict[str, Any]): The data from CV Generator.
            
        Returns:
            Dict[str, Any]: Data in CV Parser format.
        """
        if not generator_data or not isinstance(generator_data, dict):
            return {}
            
        data = generator_data.get("data", {})
        
        # Create base structure for CV Parser
        result = {
            "contact_info": {
                "first_name": data.get("firstName", ""),
                "last_name": data.get("surname", ""),
                "email": data.get("email", ""),
                "phone": data.get("phone", ""),
                "location": data.get("address", "")
            },
            "personal_statement": data.get("profileStatement", ""),
        }
        
        # Map links
        links = []
        if data.get("linkedin"):
            links.append(data.get("linkedin"))
        if data.get("website"):
            links.append(data.get("website"))
        if links:
            result["links"] = links
        
        # Map skills
        if "skills" in data and isinstance(data["skills"], list):
            result["skills"] = data["skills"]
            
        # Map experience items
        if "experience" in data and isinstance(data["experience"], list):
            result["experience"] = [
                {
                    "title": exp.get("role", ""),
                    "company": exp.get("company", ""),
                    "start_date": exp.get("startDate", ""),
                    "end_date": exp.get("endDate", ""),
                    "is_current": exp.get("current", False),
                    "description": exp.get("description", "")
                }
                for exp in data["experience"]
            ]
            
        # Map education items
        if "education" in data and isinstance(data["education"], list):
            result["education"] = [
                {
                    "institution": edu.get("institution", ""),
                    "degree": edu.get("degree", ""),
                    "start_date": edu.get("startDate", ""),
                    "end_date": edu.get("endDate", ""),
                    "grade": edu.get("grade", "")
                }
                for edu in data["education"]
            ]
        
        # Map certifications
        if "certifications" in data and isinstance(data["certifications"], list):
            result["certifications"] = [
                {
                    "name": cert.get("name", ""),
                    "issuer": cert.get("issuer", ""),
                    "date": cert.get("date", ""),
                    "description": cert.get("description", "")
                }
                for cert in data["certifications"]
            ]
        
        # Map languages
        if "languages" in data and isinstance(data["languages"], list):
            result["languages"] = [
                {
                    "language": lang.get("language", ""),
                    "proficiency": lang.get("proficiency", "")
                }
                for lang in data["languages"]
            ]
            
        # Map achievements
        if "achievements" in data and isinstance(data["achievements"], list):
            result["achievements"] = [
                {
                    "title": ach.get("title", ""),
                    "description": ach.get("description", ""),
                    "date": ach.get("date", "")
                }
                for ach in data["achievements"]
            ]
            
        return result 