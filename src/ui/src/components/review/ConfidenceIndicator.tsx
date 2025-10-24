/**
 * ConfidenceIndicator - Display confidence score with visual indicator
 *
 * Author: DevMatrix Team
 * Date: 2025-10-24
 */

import React from 'react';
import {
  FiCheckCircle,
  FiAlertTriangle,
  FiAlertCircle,
  FiAlertOctagon,
} from 'react-icons/fi';
import { GlassCard } from '../design-system/GlassCard';
import { cn } from '../design-system/utils';

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

  const getColorClass = () => {
    const level = getLevel();
    switch (level) {
      case 'high': return 'text-emerald-400';
      case 'medium': return 'text-amber-400';
      case 'low': return 'text-orange-500';
      case 'critical': return 'text-red-500';
    }
  };

  const getIcon = () => {
    const level = getLevel();
    const iconSize = size === 'small' ? 16 : size === 'large' ? 32 : 24;
    const colorClass = getColorClass();

    switch (level) {
      case 'high': return <FiCheckCircle size={iconSize} className={colorClass} />;
      case 'medium': return <FiAlertTriangle size={iconSize} className={colorClass} />;
      case 'low': return <FiAlertCircle size={iconSize} className={colorClass} />;
      case 'critical': return <FiAlertOctagon size={iconSize} className={colorClass} />;
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
    <div className="group relative flex items-center gap-2">
      {/* Icon */}
      {getIcon()}

      {/* Label */}
      {showLabel && (
        <span
          className={cn(
            'font-bold',
            getColorClass(),
            size === 'small' && 'text-xs',
            size === 'medium' && 'text-sm',
            size === 'large' && 'text-base'
          )}
        >
          {getLabel()}
        </span>
      )}

      {/* Tooltip - appears on hover */}
      <div className="absolute left-0 top-full mt-2 hidden group-hover:block z-50">
        <GlassCard className="px-3 py-2">
          <p className="text-xs text-white whitespace-nowrap">{getTooltip()}</p>
        </GlassCard>
      </div>
    </div>
  );
};

export default ConfidenceIndicator;
