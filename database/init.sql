-- Smart Home Energy Monitoring Database Schema

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create devices table
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    device_type VARCHAR(100),
    location VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create telemetry table for energy consumption data
CREATE TABLE IF NOT EXISTS telemetry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    energy_watts DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create chat_history table for storing user queries and responses
CREATE TABLE IF NOT EXISTS chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    response JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_telemetry_device_timestamp ON telemetry(device_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry(timestamp);
CREATE INDEX IF NOT EXISTS idx_devices_user_id ON devices(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history(user_id);

-- Insert sample users
INSERT INTO users (email, password_hash, first_name, last_name, role) VALUES
('admin@smarthome.com', '$2b$10$rQZ8K9vX8K9vX8K9vX8K9O', 'Admin', 'User', 'admin'),
('john@smarthome.com', '$2b$10$rQZ8K9vX8K9vX8K9vX8K9O', 'John', 'Doe', 'user'),
('jane@smarthome.com', '$2b$10$rQZ8K9vX8K9vX8K9vX8K9O', 'Jane', 'Smith', 'user')
ON CONFLICT (email) DO NOTHING;

-- Insert sample devices
INSERT INTO devices (user_id, name, device_type, location) VALUES
((SELECT id FROM users WHERE email = 'john@smarthome.com'), 'Kitchen Fridge', 'refrigerator', 'Kitchen'),
((SELECT id FROM users WHERE email = 'john@smarthome.com'), 'Living Room AC', 'air_conditioner', 'Living Room'),
((SELECT id FROM users WHERE email = 'john@smarthome.com'), 'Bedroom Light', 'light', 'Bedroom'),
((SELECT id FROM users WHERE email = 'jane@smarthome.com'), 'Office Computer', 'computer', 'Home Office'),
((SELECT id FROM users WHERE email = 'jane@smarthome.com'), 'Garage Door', 'garage_door', 'Garage')
ON CONFLICT DO NOTHING;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_devices_updated_at BEFORE UPDATE ON devices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
