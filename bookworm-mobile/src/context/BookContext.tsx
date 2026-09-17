import React, { createContext, useContext, useState } from 'react';

export type Book = {
    id: string;
    title?: string;
    author?: string;
    isbn: string | null;
    coverImage?: string;
    recognizedText?: string;
};

type BookContextType = {
    books: Book[];
    addBook: (book: Omit<Book, 'id'>) => void;
};

const BookContext = createContext<BookContextType | undefined>(undefined);

export function BookProvider({ children }: { children: React.ReactNode }) {
    const [books, setBooks] = useState<Book[]>([]);

    const addBook = (bookData: Omit<Book, 'id'>) => {
        const newBook = { ...bookData, id: Date.now().toString() };
        setBooks((prev) => [newBook, ...prev]);
    };

    return (
        <BookContext.Provider value={{ books, addBook }}>
            {children}
        </BookContext.Provider>
    );
}

export function useBooks() {
    const context = useContext(BookContext);
    if (!context) {
        throw new Error('useBooks debe usarse dentro de un BookProvider');
    }
    return context;
}