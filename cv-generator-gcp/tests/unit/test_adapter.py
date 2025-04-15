import pytest
import json
from utils.adapter import HireableCVAdapter

class TestHireableCVAdapter:
    """Test suite for the HireableCVAdapter class."""
    
    def test_parser_to_generator_basic(self):
        """Test basic conversion from parser format to generator format."""
        parser_data = {
            "contact_info": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "phone": "+44 123 456 7890",
                "location": "London, UK"
            },
            "personal_statement": "Experienced software developer with expertise in Python and cloud services.",
            "skills": ["Python", "JavaScript", "AWS", "GCP", "Docker"],
            "links": ["https://linkedin.com/in/johndoe", "https://github.com/johndoe"]
        }
        
        result = HireableCVAdapter.parser_to_generator(parser_data)
        
        assert "data" in result
        assert result["data"]["firstName"] == "John"
        assert result["data"]["surname"] == "Doe"
        assert result["data"]["email"] == "john.doe@example.com"
        assert result["data"]["phone"] == "+44 123 456 7890"
        assert result["data"]["address"] == "London, UK"
        assert result["data"]["profileStatement"] == "Experienced software developer with expertise in Python and cloud services."
        assert result["data"]["skills"] == ["Python", "JavaScript", "AWS", "GCP", "Docker"]
        assert result["data"]["linkedin"] == "https://linkedin.com/in/johndoe"
        assert result["data"]["website"] == "https://github.com/johndoe"
    
    def test_parser_to_generator_complex(self):
        """Test conversion with experience and education data."""
        parser_data = {
            "contact_info": {
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane.smith@example.com"
            },
            "experience": [
                {
                    "title": "Senior Developer",
                    "company": "Tech Co",
                    "start_date": "2020-01",
                    "end_date": "",
                    "is_current": True,
                    "description": "Leading development team."
                },
                {
                    "title": "Developer",
                    "company": "Startup Inc",
                    "start_date": "2018-03",
                    "end_date": "2019-12",
                    "is_current": False,
                    "description": "Developed web applications."
                }
            ],
            "education": [
                {
                    "institution": "University of Example",
                    "degree": "Computer Science",
                    "start_date": "2014-09",
                    "end_date": "2018-06",
                    "grade": "First Class"
                }
            ]
        }
        
        result = HireableCVAdapter.parser_to_generator(parser_data)
        
        assert "data" in result
        assert len(result["data"]["experience"]) == 2
        assert result["data"]["experience"][0]["role"] == "Senior Developer"
        assert result["data"]["experience"][0]["company"] == "Tech Co"
        assert result["data"]["experience"][0]["current"] == True
        
        assert len(result["data"]["education"]) == 1
        assert result["data"]["education"][0]["institution"] == "University of Example"
        assert result["data"]["education"][0]["degree"] == "Computer Science"
        assert result["data"]["education"][0]["grade"] == "First Class"
    
    def test_generator_to_parser_basic(self):
        """Test basic conversion from generator format to parser format."""
        generator_data = {
            "data": {
                "firstName": "Alice",
                "surname": "Johnson",
                "email": "alice.johnson@example.com",
                "phone": "+44 987 654 3210",
                "address": "Manchester, UK",
                "profileStatement": "Dedicated project manager with 5+ years experience.",
                "skills": ["Project Management", "Agile", "Scrum", "Leadership"],
                "linkedin": "https://linkedin.com/in/alicejohnson"
            }
        }
        
        result = HireableCVAdapter.generator_to_parser(generator_data)
        
        assert "contact_info" in result
        assert result["contact_info"]["first_name"] == "Alice"
        assert result["contact_info"]["last_name"] == "Johnson"
        assert result["contact_info"]["email"] == "alice.johnson@example.com"
        assert result["contact_info"]["phone"] == "+44 987 654 3210"
        assert result["contact_info"]["location"] == "Manchester, UK"
        assert result["personal_statement"] == "Dedicated project manager with 5+ years experience."
        assert result["skills"] == ["Project Management", "Agile", "Scrum", "Leadership"]
        assert result["links"] == ["https://linkedin.com/in/alicejohnson"]
    
    def test_generator_to_parser_complex(self):
        """Test conversion with experience and education data."""
        generator_data = {
            "data": {
                "firstName": "Bob",
                "surname": "Brown",
                "experience": [
                    {
                        "role": "Marketing Manager",
                        "company": "Brand Co",
                        "startDate": "2019-05",
                        "endDate": "",
                        "current": True,
                        "description": "Managing marketing campaigns."
                    }
                ],
                "education": [
                    {
                        "institution": "Marketing School",
                        "degree": "Marketing",
                        "startDate": "2015-09",
                        "endDate": "2019-06",
                        "grade": "Merit"
                    }
                ],
                "certifications": [
                    {
                        "name": "Digital Marketing",
                        "issuer": "Marketing Institute",
                        "date": "2020-01"
                    }
                ]
            }
        }
        
        result = HireableCVAdapter.generator_to_parser(generator_data)
        
        assert "experience" in result
        assert len(result["experience"]) == 1
        assert result["experience"][0]["title"] == "Marketing Manager"
        assert result["experience"][0]["company"] == "Brand Co"
        assert result["experience"][0]["is_current"] == True
        
        assert "education" in result
        assert len(result["education"]) == 1
        assert result["education"][0]["institution"] == "Marketing School"
        assert result["education"][0]["degree"] == "Marketing"
        
        assert "certifications" in result
        assert len(result["certifications"]) == 1
        assert result["certifications"][0]["name"] == "Digital Marketing"
        assert result["certifications"][0]["issuer"] == "Marketing Institute"
    
    def test_empty_data_handling(self):
        """Test handling of empty or None input data."""
        assert HireableCVAdapter.parser_to_generator(None) == {}
        assert HireableCVAdapter.parser_to_generator({}) == {}
        assert HireableCVAdapter.generator_to_parser(None) == {}
        assert HireableCVAdapter.generator_to_parser({}) == {} 