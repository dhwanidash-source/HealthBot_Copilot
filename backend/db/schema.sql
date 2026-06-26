-- HealthBot Copilot Database Schema
-- Auto-generated

CREATE UNIQUE INDEX ix_users_phone_number ON users (phone_number);

CREATE INDEX ix_users_user_id ON users (user_id);

CREATE TABLE agent_logs (
	id VARCHAR NOT NULL, 
	session_id VARCHAR, 
	agent_name VARCHAR, 
	input TEXT, 
	output TEXT, 
	execution_time FLOAT, 
	PRIMARY KEY (id)
);

CREATE TABLE campaign_engagement (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	campaign_id VARCHAR NOT NULL, 
	opened BOOLEAN, 
	clicked BOOLEAN, 
	converted BOOLEAN, 
	last_interaction DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (user_id), 
	FOREIGN KEY(campaign_id) REFERENCES campaigns (campaign_id)
);

CREATE TABLE campaigns (
	campaign_id VARCHAR NOT NULL, 
	name VARCHAR, 
	type VARCHAR, 
	target_segment VARCHAR, 
	start_date DATETIME, 
	end_date DATETIME, 
	budget FLOAT, 
	PRIMARY KEY (campaign_id)
);

CREATE TABLE chat_messages (
	message_id VARCHAR NOT NULL, 
	session_id VARCHAR NOT NULL, 
	role VARCHAR, 
	agent_name VARCHAR, 
	content TEXT, 
	timestamp DATETIME, 
	PRIMARY KEY (message_id), 
	FOREIGN KEY(session_id) REFERENCES sessions (session_id)
);

CREATE TABLE chat_summaries (
	id VARCHAR NOT NULL, 
	session_id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	summary_text TEXT, 
	embedding_vector TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES sessions (session_id), 
	FOREIGN KEY(user_id) REFERENCES users (user_id)
);

CREATE TABLE medical_history (
	id INTEGER NOT NULL, 
	user_id VARCHAR NOT NULL, 
	condition VARCHAR NOT NULL, 
	severity VARCHAR, 
	chronic_flag BOOLEAN, 
	diagnosis_date DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (user_id)
);

CREATE TABLE segments (
	id VARCHAR NOT NULL, 
	description TEXT, 
	criteria_json JSON, 
	PRIMARY KEY (id)
);

CREATE TABLE sessions (
	session_id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	start_time DATETIME, 
	end_time DATETIME, 
	channel VARCHAR, 
	context_summary TEXT, 
	PRIMARY KEY (session_id), 
	FOREIGN KEY(user_id) REFERENCES users (user_id)
);

CREATE TABLE user_allergies (
	id INTEGER NOT NULL, 
	user_id VARCHAR NOT NULL, 
	allergy_name VARCHAR NOT NULL, 
	allergy_type VARCHAR, 
	added_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (user_id)
);

CREATE TABLE user_medications (
	id INTEGER NOT NULL, 
	user_id VARCHAR NOT NULL, 
	medication_name VARCHAR NOT NULL, 
	added_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (user_id)
);

CREATE TABLE user_state (
	user_id VARCHAR NOT NULL, 
	latest_conditions VARCHAR, 
	risk_score VARCHAR, 
	engagement_score INTEGER, 
	last_updated DATETIME, 
	PRIMARY KEY (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (user_id)
);

CREATE TABLE users (
	user_id VARCHAR NOT NULL, 
	phone_number VARCHAR NOT NULL, 
	name VARCHAR, 
	age INTEGER, 
	gender VARCHAR, 
	location VARCHAR, 
	lifestyle_type VARCHAR, 
	bmi FLOAT, 
	smoking_status VARCHAR, 
	exercise_frequency VARCHAR, 
	risk_score VARCHAR, 
	engagement_score INTEGER, 
	churn_risk VARCHAR, 
	lifetime_value FLOAT, 
	preferred_channel VARCHAR, 
	consent_flag BOOLEAN, 
	created_at DATETIME, city TEXT DEFAULT 'Not Specified', 
	PRIMARY KEY (user_id)
);

CREATE TABLE visits (
	visit_id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	hospital_id VARCHAR, 
	visit_date DATETIME, 
	purpose VARCHAR, 
	doctor_notes TEXT, 
	followup_required BOOLEAN, 
	PRIMARY KEY (visit_id), 
	FOREIGN KEY(user_id) REFERENCES users (user_id)
);

