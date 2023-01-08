def horner(polynomial, binomial):
    # Example:
    # polynomial            P(x) = 4(x**3)-2(x**2)+x-3
    # divided by binomial   (x-1)
    # root = 1
    #
    #          v~~~~~v~~~~~v~~~~~v~~~~ coefficients
    # +-----+-----+-----+-----+-----+
    # |     |  4  | -2  |  1  | -3  |
    # +-----+-----+-----+-----+-----+
    # |  1  |  4  |  2  |  3  |  0  |
    # +-----+-----+-----+-----+-----+
    #    ^~~~~~ root             ^~~~~~ remainder
    #
    #
    # quotient   Q(x) = 4(x**2) + 2x + 3
    # remainder  R(x) = 0
    #
    # Hence 4(x**3)-2(x**2)+x-3 = (x-1)(4(x**2)+2x+3)
    # And the polynomial is divisible by the binomial, because remainder == 0.
    coef_1, *coeffs = polynomial.coeffs
    root = -binomial.transform.rhs
    quotient = [coef_1]
    for coef in coeffs:
        quotient.append(quotient[-1] * root + coef)
    remainder = quotient.pop()
    return quotient, remainder
