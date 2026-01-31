const Card = ({ children, className = '', hover = false, padding = true }) => {
    return (
        <div
            className={`
        bg-white rounded-xl border border-gray-200 shadow-sm
        ${hover ? 'hover:shadow-md transition-shadow duration-200' : ''}
        ${padding ? 'p-6' : ''}
        ${className}
      `}
        >
            {children}
        </div>
    );
};

export default Card;