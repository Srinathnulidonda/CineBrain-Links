const Loader = ({ size = 'md', text = '' }) => {
    const sizes = {
        sm: 'w-6 h-6',
        md: 'w-10 h-10',
        lg: 'w-16 h-16',
    };

    return (
        <div className="flex flex-col items-center justify-center gap-3">
            <div className={`${sizes[size]} relative`}>
                <div className="absolute inset-0 rounded-full border-4 border-gray-200"></div>
                <div className="absolute inset-0 rounded-full border-4 border-primary-600 border-t-transparent animate-spin"></div>
            </div>
            {text && <p className="text-gray-600 text-sm font-medium">{text}</p>}
        </div>
    );
};

export default Loader;