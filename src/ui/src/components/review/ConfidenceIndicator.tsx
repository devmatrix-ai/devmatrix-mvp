/**
 * ConfidenceIndicator - Display confidence score with visual indicator
 *
 * Author: DevMatrix Team
 * Date: 2025-10-24
 */

import React from 'react';
import { Box, Tooltip, Typography } from '@mui/material';
import {
  CheckCircle as HighIcon,
  Warning as MediumIcon,
  Error as LowIcon,
  Dangerous as CriticalIcon,
} from '@mui/icons-material';

interface ConfidenceIndicatorProps {
  score: number; // 0.0-1.0
  showLabel?: boolean;
  size?: 'small' | 'medium' | 'large';
}

const ConfidenceIndicator: React.FC<ConfidenceIndicatorProps> = ({
  score,
  showLabel = true,
  size = 'medium',
}) => {
  // Determine level and color
  const getLevel = () => {
    if (score >= 0.85) return 'high';
    if (score >= 0.70) return 'medium';
    if (score >= 0.50) return 'low';
    return 'critical';
  };

  const getColor = () => {
    const level = getLevel();
    switch (level) {
      case 'high': return '#4caf50'; // green
      case 'medium': return '#ff9800'; // orange
      case 'low': return '#ff5722'; // deep orange
      case 'critical': return '#f44336'; // red
    }
  };

  const getIcon = () => {
    const level = getLevel();
    const iconSize = size === 'small' ? 16 : size === 'large' ? 32 : 24;

    switch (level) {
      case 'high': return <HighIcon sx={{ fontSize: iconSize, color: getColor() }} />;
      case 'medium': return <MediumIcon sx={{ fontSize: iconSize, color: getColor() }} />;
      case 'low': return <LowIcon sx={{ fontSize: iconSize, color: getColor() }} />;
      case 'critical': return <CriticalIcon sx={{ fontSize: iconSize, color: getColor() }} />;
    }
  };

  const getLabel = () => {
    const level = getLevel();
    return `${(score * 100).toFixed(0)}% (${level})`;
  };

  const getTooltip = () => {
    const level = getLevel();
    switch (level) {
      case 'high':
        return 'High confidence - No review needed';
      case 'medium':
        return 'Medium confidence - Optional review';
      case 'low':
        return 'Low confidence - Review recommended';
      case 'critical':
        return 'Critical - Review required';
    }
  };

  return (
    <Tooltip title={getTooltip()} arrow>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
        }}
      >
        {getIcon()}
        {showLabel && (
          <Typography
            variant={size === 'small' ? 'caption' : 'body2'}
            sx={{
              fontWeight: 'bold',
              color: getColor(),
            }}
          >
            {getLabel()}
          </Typography>
        )}
      </Box>
    </Tooltip>
  );
};

export default ConfidenceIndicator;
