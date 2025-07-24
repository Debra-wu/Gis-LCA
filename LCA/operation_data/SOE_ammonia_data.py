

impact_assessment_result_dict = {
    "Fine particulate matter formation": {"amount": 0.00029, "unit": "kg PM2.5 eq"},
    "Fossil resource scarcity": {"amount": 0.063913, "unit": "kg oil eq"},
    "Freshwater ecotoxicity": {"amount": 0.056401, "unit": "kg 1,4-DCB"},
    "Freshwater eutrophication": {"amount": 0.000208, "unit": "kg P eq"},
    "Global warming": {"amount": 0.269179, "unit": "kg CO2 eq"},
    "Human carcinogenic toxicity": {"amount": 0.000884, "unit": "kg 1,4-DCB"},
    "Human non-carcinogenic toxicity": {"amount": 0.116101, "unit": "kg 1,4-DCB"},
    "Ionizing radiation": {"amount": 0.010943, "unit": "kBq Co-60 eq"},
    "Land use": {"amount": 0.121758, "unit": "m2a crop eq"},
    "Marine ecotoxicity": {"amount": 2.042849, "unit": "kg 1,4-DCB"},
    "Marine eutrophication": {"amount": 0.000124, "unit": "kg N eq"},
    "Mineral resource scarcity": {"amount": 0.000009, "unit": "kg Cu eq"},
    "Ozone formation, Human health": {"amount": 0.000291, "unit": "kg NOx eq"},
    "Ozone formation, Terrestrial ecosystems": {"amount": 0.000294, "unit": "kg NOx eq"},
    "Ozone layer depletion": {"amount": 3.3e-07, "unit": "kg CFC11 eq"},
    "Photochemical ozone formation": {"amount": 0.000294, "unit": "kg SO2 eq"},
    "Terrestrial acidification": {"amount": 0.001172, "unit": "kg 1,4-DCB"},
    "Water consumption": {"amount": 0.01579, "unit": "m3"}
}


CO2_result_dict = {
    "Ammonia production, SOE electrolysis": {"amount": 2.6, "unit": "kg CO2 eq"},
    "Electricity, medium voltage, from grid": {"amount": 0.92, "unit": "kg CO2 eq"},
    "Water, deionised, from tap water, at plant": {"amount": 0.0051, "unit": "kg CO2 eq"},
    "Oxygen, liquid, production": {"amount": 0.008, "unit": "kg CO2 eq"},
    "Nitrogen, liquid, production": {"amount": 0.0051, "unit": "kg CO2 eq"},
    "Hydrogen, from SOE electrolysis": {"amount": 2.2, "unit": "kg CO2 eq"},
    "CO2, captured": {"amount": -0.72, "unit": "kg CO2 eq"},
    "Heat, district or industrial, natural gas": {"amount": 0.22, "unit": "kg CO2 eq"},
    "Transport, freight, lorry, Euro6": {"amount": 0.09, "unit": "kg CO2 eq"}
}


normalized_impact_dict = {
    "Global warming": {"amount": 0.269179, "unit": "%"},
    "Stratospheric ozone depletion": {"amount": 3.3e-07, "unit": "%"},
    "Ionizing radiation": {"amount": 0.010943, "unit": "%"},
    "Ozone formation, Human health": {"amount": 0.000291, "unit": "%"},
    "Fine particulate matter formation": {"amount": 0.00029, "unit": "%"},
    "Ozone formation, Terrestrial ecosystems": {"amount": 0.000294, "unit": "%"},
    "Terrestrial acidification": {"amount": 0.001172, "unit": "%"},
    "Freshwater eutrophication": {"amount": 0.000208, "unit": "%"},
    "Marine eutrophication": {"amount": 0.000124, "unit": "%"},
    "Terrestrial ecotoxicity": {"amount": 0.00024, "unit": "%"},
    "Freshwater ecotoxicity": {"amount": 0.056401, "unit": "%"},
    "Marine ecotoxicity": {"amount": 2.042849, "unit": "%"},
    "Human carcinogenic toxicity": {"amount": 0.000884, "unit": "%"},
    "Human non-carcinogenic toxicity": {"amount": 0.116101, "unit": "%"},
    "Land use": {"amount": 0.121758, "unit": "%"},
    "Water consumption": {"amount": 0.01579, "unit": "%"},
    "Mineral resource scarcity": {"amount": 0.000009, "unit": "%"},
    "Fossil resource scarcity": {"amount": 0.063913, "unit": "%"}
}
