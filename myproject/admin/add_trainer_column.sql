-- Add trainer_id column to teams table
ALTER TABLE teams ADD COLUMN IF NOT EXISTS trainer_id UUID REFERENCES users(user_id) ON DELETE SET NULL;

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_teams_trainer ON teams (trainer_id);
