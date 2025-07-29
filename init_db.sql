-- Sample database schema for testing the API
-- This creates some sample tables with survey data

-- Create surveys table
CREATE TABLE IF NOT EXISTS surveys (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    created_date DATE DEFAULT CURRENT_DATE,
    status VARCHAR(50) DEFAULT 'active'
);

-- Create responses table
CREATE TABLE IF NOT EXISTS responses (
    id SERIAL PRIMARY KEY,
    survey_id INTEGER REFERENCES surveys(id),
    respondent_age INTEGER,
    respondent_gender VARCHAR(20),
    response_text TEXT,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create demographics table
CREATE TABLE IF NOT EXISTS demographics (
    id SERIAL PRIMARY KEY,
    survey_id INTEGER REFERENCES surveys(id),
    age_group VARCHAR(20),
    gender VARCHAR(20),
    location VARCHAR(100),
    education_level VARCHAR(50),
    income_range VARCHAR(50)
);

-- Insert sample data
INSERT INTO surveys (title, description) VALUES 
('Customer Satisfaction Survey', 'Annual customer satisfaction survey for our services'),
('Product Feedback Survey', 'Feedback collection for new product features'),
('Employee Engagement Survey', 'Internal survey to measure employee satisfaction');

INSERT INTO responses (survey_id, respondent_age, respondent_gender, response_text, rating) VALUES 
(1, 25, 'Female', 'Very satisfied with the service quality', 5),
(1, 34, 'Male', 'Good service but room for improvement', 4),
(1, 28, 'Female', 'Average experience', 3),
(2, 22, 'Male', 'Love the new features!', 5),
(2, 45, 'Female', 'Features are useful but complex', 4),
(3, 31, 'Male', 'Good work environment', 4),
(3, 29, 'Female', 'Satisfied with current role', 4);

INSERT INTO demographics (survey_id, age_group, gender, location, education_level, income_range) VALUES 
(1, '25-34', 'Female', 'New York', 'Bachelor', '$50-75k'),
(1, '35-44', 'Male', 'California', 'Master', '$75-100k'),
(1, '25-34', 'Female', 'Texas', 'Bachelor', '$40-65k'),
(2, '18-24', 'Male', 'Florida', 'High School', '$25-40k'),
(2, '45-54', 'Female', 'Illinois', 'PhD', '$100k+'),
(3, '25-34', 'Male', 'Washington', 'Bachelor', '$60-85k'),
(3, '25-34', 'Female', 'Oregon', 'Master', '$70-95k');

-- Create indexes for better query performance
CREATE INDEX idx_responses_survey_id ON responses(survey_id);
CREATE INDEX idx_demographics_survey_id ON demographics(survey_id);
CREATE INDEX idx_responses_submitted_at ON responses(submitted_at);

-- Grant permissions (for production, use more restrictive permissions)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO survey_user;
