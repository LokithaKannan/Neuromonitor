import './Card.css';

export default function Card({ children, className = '', padding = true, ...rest }) {
  return (
    <div className={`card ${padding ? 'card--padded' : ''} ${className}`} {...rest}>
      {children}
    </div>
  );
}
